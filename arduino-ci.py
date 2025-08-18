import argparse
import json
import logging
import os
import re
import shutil
import sys
import subprocess
import yaml

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

class CiMatrixConfig:
    """
    Class to parse the CI compile sketches configuration file.

    The yaml file uses the following keys:

        - sketch: 
            List sketched to be compiled.

            This key is optional. 
            If not present the sketches will
            be discovered in the sketch default paths. Those are:
                - for cores -> "libraries"
                - for libraries -> "examples"

            Format:         
                - directory path which contains sketches. The path should be
                relative to the asset root path.
                - .ino sketch path. The path should be relative to the asset root path.
                Example:
                sketch:
                    - SPI/examples/
                    - examples/some_example/some_example.ino

        - fqbn: 
            List of boards with format <vendor>:<arch>:<board> against which
            the "sketch" list will be compiled.

            This key is optional.
            If not present the fqbn values will:
                - for cores- > be discovered in the "boards.txt" file
                - for libraries -> use the defined in the default 
                "config/ci-config-matrix-ifx-lib.yml" provided in this repository.
            
            Format:
                - <vendor>:<arch>:<board>
                Example:
                    fqbn:
                        - vendor:avr:board
                        - vendor:esp32:board
        
        - include:
            List of dictionaries with key-value pairs which extend the 
            compile fqbn-sketch matrix. 
            
            This key is optional. 
            Each dictionary of the list can be a list of key-values pairs, 
            or a single key-value pair.
            Each modify the default matrix in a different way:

            - Pair of keys: A dictionary with a "fqbn" and "sketch" key. Those 
            combinations of "fqbn-sketch" (if not already present) will also be
            added to the default matrix. 

            - Single keys: A dictionary with either "fqbn" or "sketch" key. The
            values will them be then simply extend the default matrix key. 
            This is mainly useful when the main matrix is automatically discovered, 
            and these particular values are "not discoverable".

            The allowed keys are "fqbn" and "sketch". 
            The value formats allowed are the same as the root node keys. 
            But in this case, the value can be a list (of scalars) or a scalar.

            Example:
                include:
                    # Example of pair of keys to add sketches which 
                    # should only be compiled for a specific board
                    - fqbn: vendor:avr:board   # The value of this key can be a scalar or list
                      sketch:                  # The value of this key can be a scalar or list
                        - additional_sketch/additional_sketch.ino
                        - extra_example/extra_example.ino
                    # A sketch which should be compiled for all the boards
                    # and not discoverable in the default paths
                    - sketch: some_hidden_path_sketch/some_hidden_path_sketch.ino

        - exclude:
            List of dictionaries with key-value pairs which will be excluded from the
            default fqbn-sketch matrix.

            This key is optional.
            Each dictionary of the list can be a list of key-values pairs, 
            or a single key-value pair.
            Each modify the default matrix in a different way:

            - Pair of keys: A dictionary with a "fqbn" and "sketch" key. Those 
            combinations of "fqbn-sketch" (if present) will
            will be removed from the default matrix. 

            - Single keys: A dictionary with either "fqbn" or "sketch" key. The
            values will them be then (if present) removed from the default matrix key. 
            This is mainly useful when the main matrix is automatically discovered, 
            and these particular values are "not discoverable".

            The allowed keys are "fqbn" and "sketch". 
            The value formats allowed are the same as the root node keys. 
            But in this case, the value can be a list (of scalars) or a scalar.

            Example:
                exclude:
                    # Example of pair of keys to remove sketches which 
                    # not applicable for a specific board
                    - fqbn: vendor:avr:board    # The value of this key can be a scalar or list
                      sketch:                   # The value of this key can be a scalar or list
                        - SPI/examples/SPI_mode_not_available_for_this_board.ino
                        - SPI/examples/SPI_mode2_not_available_for_this_board.ino
                    # A sketch which should be compiled for all the boards
                    # and not discoverable in the default paths
                    - sketch: I2C/examples/i2c_example_with_bug/i2c_example_with_bug.ino

        - asset_type:
            The type of the Arduino asset. 
            The allowed values are "library" and "core". 

            This key is optional. 
            If not present, the asset type will be discovered based on the existence of 
            files required by the Arduino library or platform specifications.
                - library: "library.properties" file 
                - core: "platform.txt" and "board.txt" files and "cores" and "variants" directories.
        
            Example:
                asset_type: library

        - additional_urls:
            List of dictionaries with key-value pairs with the the keys "core" and "url".
            This key is optional. 
            The "core" key is the name of the core to be installed, with format <vendor>:<arch>.
            The "url" key is the url pointing to the package index json file required by Arduino 
            to install third-party cores.

            Example:
                additional_urls:
                    - core: esp32:esp32
                      url: https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json

    """
    def __init__(self, ci_matrix_yml, asset_root_path):
        """
        Constructor of the CI compile matrix configuration class.

        The ci matrix yaml file is parsed and the configuration is 
        stored in a dictionary.

        For cores, the ci matrix file is optional. If the file is not present, 
        or if values for they main keys "fqbn" and/or "sketch", these
        will be discovered automatically.

        For libraries, a list of "fqbn" is not discoverable. 
        A default one is set in config for Infineon libraries to make it the need
        of a ci matrix config file optional.

        The asset type is also discovered automatically based on:
            - For libraries, the "sketch" list will be searched in the "examples" folder.
            The "fqbn" list needs to be provided. Therefore, at least the yml file,
            with the set of "fqbn" is required for libraries.

            - For cores, the directory to search for the "sketch" list is "libraries".
            The "fqnb" list is extracted from the "boards.txt" file.

        Additionally, if not specified, the asset type is also automatically detected. 
        The asset type can be either a "library" or a "core". A library is considered when
        the "library.properties" file is present in the asset root path. 
        A core is considered when the "platform.txt" and "board.txt" files and
        the "cores" and "variants" directories are present in the asset root path.

        Args:
         - ci_matrix_yml (str): The name (including path) the CI matrix configuration file.
         - asset_root_path (str): The path to the Arduino asset root directory.
        """
        self.ci_matrix_file = ci_matrix_yml
        self.config = {}
        self.asset_root_path = asset_root_path
        self.extra_sketch_paths = []
        self.sketch_core_default_path = ["libraries"]
        self.sketch_library_default_path = ["examples"]
        self.asset_type = None

        if ci_matrix_yml is not None:
            self.config = self.__parse_config()

        if "asset_type" in self.config:
            self.asset_type = self.config["asset_type"]
        else:
            self.__asset_type_discover()

        if "fqbn" not in self.config:
            self.config["fqbn"] = self.__fqbn_list_default()
        
        if "sketch" not in self.config:
            self.config["sketch"] = self.__sketch_list_default()

    def __str__(self):
        """Returns json not formatted"""
        return str(self.config)

    def __str__as_yml(self):
        """Uses yaml dump to generate a string"""
        return yaml.dump(self.config, indent=4, default_flow_style=False)
    
    def __str__as_json_pretty(self):
        """Uses json dump to generate a pretty string"""
        return json.dumps(self.config, indent=4)

    def get_list(self, query_key, filter=None):
        """
        List all the elements of a given key ("fqbn" or "sketch") in the configuration matrix.
        If a filter is provided, it will filter the list based on the value of filter key.
        The list is sorted in alphabetical order.

        Args:
            - query_key (str): The key to be queried. The allowed keys are "fqbn" and "sketch".
            - filter (str): The filter to be applied. The format should be "key=value".

        Returns:
            - queried_list (dict): A dictionary with the queried key and the list of values.
            - If the key is not present in the configuration matrix, an dictionary with an empty list
            will be returned.
        """

        queried_list = { query_key: [] }

        if self.__is_key_valid(query_key):
            
            if filter is None:
                queried_list = self.__query(query_key)
            else:
                queried_list = self.__filtered_query(query_key, filter)

        queried_list[query_key] = sorted(queried_list[query_key], key=str.lower)
        
        return queried_list

    def get_additional_url(self, core):
        """
        Gets the additional url for a given core.
        Args:
            - core (str): The core to be queried. The format should be <vendor>:<arch>.
        Returns:
            - url (str): The url for the core.
            - None if the core is not found in the additional urls list.
        """
        if "additional_urls" in self.config:
            for node in self.config["additional_urls"]:
                if "core" in node:
                    if node["core"] == core:
                        return node["url"]
        return None

    """ Private methods """

    def __parse_config(self):
        """
        Parses the matrix ci yml file and returns the config as a dictionary.
        """
        config = {}
        try:
            with open(self.ci_matrix_file, "r") as f:
                config = yaml.safe_load(f)
                if config is None:
                    config = {}
        except FileNotFoundError:
            logging.warning("The ci matrix config file was not found. Default or discovered \"sketches\" and/or \"fqbn\" will be used.")

        return config

    def __fqbn_list_default(self):
        """
        Discover the fqbn list based on the asset type.

        Returns:
            - fqbn_list (list): A list of fqbn.
        """

        def library_fqbn_list_default():
            """
            Discover the fqbn list for libraries.
            The fqbn list is loaded from the config/ci-config-matrix-ifx-lib.yml file.
            The file should contain a list of fqbn and additional urls (for third party cores).

            Returns:
                - fqbn_list (list): A list of fqbn.
            """
            fqbn_list = []

            fqbn_ifx_lib_default_yml = os.path.join(os.path.dirname(__file__),"config", "ci-config-matrix-ifx-lib.yml")
            try: 
                with open(fqbn_ifx_lib_default_yml, "r") as f:
                    logging.warning(f"Loading IFX default library fqbn list from \"{fqbn_ifx_lib_default_yml}\"")
                    fqbn_ifx_lib_default = yaml.safe_load(f)
                    
                    fqbn_list = fqbn_ifx_lib_default["fqbn"]
                    
                    if "additional_urls" in fqbn_ifx_lib_default:
                        if "additional_urls" not in self.config:
                            self.config["additional_urls"] = []
                        self.config["additional_urls"].extend(fqbn_ifx_lib_default["additional_urls"])
            except FileNotFoundError:
                logging.error(f"\"{fqbn_ifx_lib_default_yml}\" file not found")
                sys.exit(1)

            return fqbn_list
        
        def core_fqbn_list_auto_discovery():
            """
            Discover the fqbn list for cores.
            The board name list is loaded from the boards.txt file.
            The vendor and architecture are loaded from the package index template file.
            These are combined to create the fqbn list.

            Returns:
                - fqbn_list (list): A list of fqbn.
            """

            def load_board_txt():
                """
                Loads the content of the boards.txt file.
                If the file is not present, it will exit the program on error.

                Returns:
                    - boards_txt_content (str): The content of the boards.txt file.
                """
                boards_txt = os.path.exists(os.path.join(self.asset_root_path, "boards.txt"))
                if not boards_txt:
                    logging.error(f"\"boards.txt\" file not found in the asset root path \"{self.asset_root_path}\"")
                    sys.exit(1)
                
                # Load content of boards.txt file
                with open(os.path.join(self.asset_root_path, "boards.txt"), "r") as f:
                    boards_txt_content = f.read()
                
                return boards_txt_content

            def get_board_name_list(boards_txt_content):
                """
                The function will get the board name list from the boards.txt content.
                The board name is the prefix of the line with the pattern:
                
                <prefix>.name=<board_name>

                Args: 
                    - boards_txt_content (str): The content of the boards.txt file.
                
                Returns:
                    - board_name_list (list): A list of board names.
                """
                board_name_list = []

                for line in boards_txt_content.splitlines():
                    # Skip comments and empty lines
                    if line.startswith("#") or line.strip() == "":
                        continue
                    if ".name=" in line:
                        prefix = line.split(".name=")[0].strip()
                        if prefix not in board_name_list:
                            board_name_list.append(prefix)

                # Remove duplicates
                board_name_list = list(set(board_name_list))

                return board_name_list
            
            def get_vendor_core_name():
                """
                The vendor and core name are extracted from the package index template file.
                The file should be in the "package" directory of the asset root path.
                The JSOn file should contain in the name the the substring "package" and "index".
                The file should be a json file with the following structure:
                {
                    "packages": [
                        {
                            "name": "<vendor>",
                            "platforms": [
                                {
                                    "architecture": "<arch>"
                                }
                            ]
                        }
                    ]
                }
                
                Returns:
                    - vendor_name (str): The vendor name.
                    - arch_name (str): The architecture name.
                """
                # Find vendor and core name
                package_index_template_dir = os.path.join(self.asset_root_path, "package")
                if not os.path.exists(package_index_template_dir):
                    logging.error(f"\"package\" dir not found in the asset root path \"{self.asset_root_path}\"")
                    sys.exit(1)

                # Find in the dir a .json file
                for root, dirs, files in os.walk(package_index_template_dir):
                    for file in files:
                        if file.endswith(".json") and "package" in file and "index" in file:
                            package_index_template_file = os.path.join(root, file)
                            break

                # Load content of package_index_template_file   
                with open(package_index_template_file, "r") as f:
                    package_index_template_content = json.load(f)

                try:
                    vendor_name = package_index_template_content["packages"][0]["name"]
                    arch_name = package_index_template_content["packages"][0]["platforms"][0]["architecture"]
                except KeyError:
                    logging.error(f"Key not found in the package index template file \"{package_index_template_file}\"")
                    sys.exit(1)

                return vendor_name, arch_name

            """
            Main core fqbn list discovery function.
            """
            fqbn_list = []

            boards_txt_content = load_board_txt()
            board_name_list = get_board_name_list(boards_txt_content)
            vendor_name, arch_name = get_vendor_core_name()

            for board in board_name_list:
                fqbn = f"{vendor_name}:{arch_name}:{board}"
                fqbn_list.append(fqbn)

            return fqbn_list
        
        """
        Main function to discover the fqbn list based on the asset type.
        """

        fqbn_list = []
        if self.asset_type == "library":
           fqbn_list =  library_fqbn_list_default()
        elif self.asset_type == "core":
           fqbn_list = core_fqbn_list_auto_discovery()
        else:
            logging.error(f"Asset type \"{self.asset_type}\" not supported. Supported types are: \"library\" and \"core\"")
            sys.exit(1)
        
        return fqbn_list

    def __sketch_list_default(self):
        """
        Discover the sketch list based on the asset type.
        The list is generated based on the default sketch paths.
        The sketch paths are:
            - For libraries: "examples"
            - For cores: "libraries"
        The sketch paths are relative to the asset root path.

        Returns:
            - sketch_list (list): A list of sketches.
        """
        def sketch_list_auto_discovery(sketch_path_list):
            """
            Walks through the directories in the sketch path list and
            returns a list of all the .ino files found in the directories.

            Args:
                sketch_path_list (list of str): List of directories to search for sketches.
            """
            sketch_list = []

            for sketch_path in sketch_path_list:
                sketch_path_abs = os.path.join(self.asset_root_path, sketch_path)
                if not os.path.exists(sketch_path_abs):
                    logging.warning(f"\"{sketch_path}\" dir not found in the asset root path \"{self.asset_root_path}\"")
            
                # Walk through all the directories in the library path
                # and list all the files with the .ino extension
                for root, dirs, files in os.walk(sketch_path_abs):
                    for file in files:
                        if file.endswith(".ino"):
                            # Append only relative path to the asset root path
                            # to avoid absolute path in the sketch list
                            sketch_with_full_path = os.path.join(root, file)
                            sketch_with_relative_path = os.path.relpath(sketch_with_full_path, self.asset_root_path)
                            # Exchange backslash with forward slash (in case of Windows)
                            sketch_with_relative_path = sketch_with_relative_path.replace("\\", "/")
                            sketch_list.append(sketch_with_relative_path)
        
            return sketch_list

        """
        Main function to discover the sketch list based on the asset type.
        """

        sketch_list = []
        if self.asset_type == "library":
           sketch_list = sketch_list_auto_discovery(self.sketch_library_default_path)
        elif self.asset_type == "core":
           sketch_list = sketch_list_auto_discovery(self.sketch_core_default_path)
        else:
            logging.error(f"Asset type \"{self.asset_type}\" not supported. Supported types are: \"library\" and \"core\"")
            sys.exit(1)
        
        return sketch_list


    def __asset_type_discover(self):
        """
        Discover the asset type based on the root path content,
        and set the asset type in the configuration matrix.
        The asset type can be either a library or a core.
            - A library is considered when the "library.properties" file is present in the asset root path.
            - A core is considered when the "platform.txt" and "board.txt" files and
            the "cores" and "variants" directories are present in the asset root path.
        """
        if os.path.exists(os.path.join(self.asset_root_path, "library.properties")):
            self.asset_type = "library"
        elif os.path.exists(os.path.join(self.asset_root_path, "platform.txt")) and \
             os.path.exists(os.path.join(self.asset_root_path, "boards.txt")) and \
             os.path.exists(os.path.join(self.asset_root_path, "variants")) and \
             os.path.exists(os.path.join(self.asset_root_path, "cores")):
            self.asset_type = "core"
        else:
            logging.error(f"Asset type not found. The asset root path \"{self.asset_root_path}\" does not contain a valid library or core.")
            sys.exit(1) 

    def __is_key_valid(self, key):
        """
        Validate the key. 
        - The queryable keys are "fqbn" and "sketch".
        The rest are not added, as they are modifier for the of the default 
        matrix or other config parameters.
        - The key needs to also present at least in the "include" key.

        Args:
            key (str): The key to be validated.

        Returns:
            - True if the key is valid.
            - False if the key is not valid.
        """        
        allowed_list_keys = ["fqbn", "sketch"]

        if key not in allowed_list_keys:
            logging.error(f"Key \"{key}\" is not allowed. Allowed keys are: \"{allowed_list_keys}\"")
            return False

        key_in_config = False
        if key in self.config:
            key_in_config = True
        else:
            if "include" in self.config:
                for entry in self.config["include"]:
                    if key in entry:
                        key_in_config = True
                        break
        
        if not key_in_config:
            logging.error(f"Key \"{key}\" not found in the configuration matrix")
            return False

        return True

    def __get_values_from_root_node_key(self, key):
        """
        Get the values from a dictionary key in the root node of the 
        configuration matrix.
        The value is always lists of scalars for root main matrix keys
        "fqbn" and "sketch".
        Args: 
            - key (str): The key to be queried. The allowed keys are "fqbn" and "sketch".

        Returns:
            - values (list): A list of values for the queried key.
        """
        values = []

        if key in self.config:
            values = self.config[key]

        return values

    def __get_values_from_modifier_node_key(self, node, key, single_key_check=False):
        """
        Get the values from a dictionary key modifying the main fqbn-sketch matrix.
        These "modifier" nodes are "include" and "exclude".
        These values always contain a list of dictionaries.
        The dictionaries can contain either a pair of keys or a single key.
        The pair of keys are "fqbn" and "sketch". 
        The single key can be either "fqbn" or "sketch".

        Args:
            - node (str): The node to be queried. The allowed nodes are "include" and "exclude".
            - key (str): The key to be queried. The allowed keys are "fqbn" and "sketch".
            - single_key_check (bool): If True, it will return the key only if it is a single key.

        Returns:
            - values (list): A list of values for the queried key.
        """
        def single_pair_key_check(node, single_key_check):
            if single_key_check:
                if len(node) != 1:
                    return False

            return True

        values = []

        if node in self.config:
            # This should always be a list of dictionaries
            for item in self.config[node]:
                if key in item and single_pair_key_check(item, single_key_check):
                    # This can be an str scalar or a list
                    if isinstance(item[key], list):
                        values.extend(item[key])
                    else:
                        values.append(item[key])
        return values

    def __get_filtered_values_from_modifier_node_key(self, node, query_key, filter_key, filter_value):
        """
        Get the values from a dictionary key modifying the main fqbn-sketch matrix matching a filter.
        If the filter key-value pair present in one of the dictionaries of the list in the node, 
        then the queried key value of that dictionary will be returned.
        The node is either "include" or "exclude".
        The child node needs to have both the filter key and the query key.

        Args:
            - node (str): The node to be queried. The allowed nodes are "include" and "exclude".
            - query_key (str): The key to be queried. The allowed keys are "fqbn" and "sketch".
            - filter_key (str): The key to be filtered. The allowed keys are "fqbn" and "sketch".
            - filter_value (str): The value to be filtered.
        
        Returns:
            - values (list): A list of values for the queried key.
        """
        values = []

        if node in self.config:
            # This should always be a list of dictionaries
            # For filtered values the node should have a pair 
            # of key-value pairs
            # The child node should have a query_key dictionary (but still is checked)
            for child_node in self.config[node]:
                if filter_key in child_node and \
                   filter_value in child_node[filter_key] and \
                   query_key in child_node:
                        # This can be an str scalar or a list
                        if isinstance(child_node[query_key], list):
                            values.extend(child_node[query_key])
                        else:
                            values.append(child_node[query_key])
        
        return values

    def __query(self, query_key):
        """
        Gets the list of values for the queried key.
        The list of values is generated based on the following rules:
        - The values from the root node key are always included.
        - The values from the include node are also included.
        - The values from the exclude node are removed from list when both of
        these conditions are met:
            - The value present in the root node and or the include node.
            - The value is a single key in the exclude node.

        Args:
            - query_key (str): The key to be queried. The allowed keys are "fqbn" and "sketch".
        
        Returns:
            - queried_list (dict): A dictionary with the queried key and the list of values.
            - If the key is not present in the configuration matrix, an dictionary with an empty list
            will be returned.
        """
        queried_list = { query_key: [] }

        # Values from key in root node 
        root_node_key_values = self.__get_values_from_root_node_key(query_key)
        queried_list[query_key].extend(root_node_key_values)

        # Values from key in include node
        include_values = self.__get_values_from_modifier_node_key("include", query_key)
        queried_list[query_key].extend(include_values)
        # Remove duplicates
        queried_list[query_key] = list(set(queried_list[query_key]))

        # Values to exclude if present in the exclude node as single key
        exclude_values = self.__get_values_from_modifier_node_key("exclude", query_key, single_key_check=True)
        # Remove the values if they are in the queried_list
        queried_list[query_key] = [ item for item in queried_list[query_key] if item not in exclude_values ]

        return queried_list

    def __query_same_list_and_filter_key(self, query_filter_key, filter_value):
        """
        Gets the value for the queried key and filter key.
        As the key is the same, this is a simple query, which will return the value
        if that is present in the list of values for the queried key.

        Args:
            - query_filter_key (str): The key to be queried and filtered. The allowed keys are "fqbn" and "sketch".
            - filter_value (str): The value to be filtered.
        Returns:
            - queried_list (dict): A dictionary with the queried key and the list of values.
            - If the key is not present in the configuration matrix, an dictionary with an empty list
            will be returned.
        """
        queried_list = { query_filter_key: [] }

        queried_key_values = self.__query(query_filter_key)
        if filter_value in queried_key_values[query_filter_key]:
            queried_list[query_filter_key] = [ filter_value ]

        return queried_list
            
    def __query_diff_list_and_filter_key(self, query_key, filter_key, filter_value):
        """
        Gets the list of values for the queried key and a filter key. 
        The query key and filter key are different.

        The list of values is generated based on the following rules:
        - When the filter value is present in the root node key, the complete list of 
        the queried key in the root node will be added.
        - When the filter value is present in the include node as single key, 
        the complete list of the queried key in the root node will be added.
        - When the query key is present in the include node as single key and there is
        already a query list, the values from the include node will be added to the list.
        - When the filter value is present in the include node as pair of keys, the value 
        of the query key will be added to the list.
        - When the filter value is present in the exclude node as pair of keys, the value of
        the query key will be removed from the list (if existing in the queried list).
        - When the query key is present in the exclude node as single key, the value of the 
        query key will be removed from the list (if existing in the queried list).

        Args:
            - query_key (str): The key to be queried. The allowed keys are "fqbn" and "sketch".
            - filter_key (str): The key to be filtered. The allowed keys are "fqbn" and "sketch".
            - filter_value (str): The value to be filtered.
        
        Returns:
            - queried_list (dict): A dictionary with the queried key and the list of values.
            - If the key is not present in the configuration matrix, an dictionary with an empty list
            will be returned.
        """
        queried_list = { query_key: [] }

        exclude_filter_values = self.__get_values_from_modifier_node_key("exclude", filter_key, single_key_check=True)
        if filter_value in exclude_filter_values:
            return queried_list

        root_node_key_values = self.__get_values_from_root_node_key(filter_key)
        include_filter_values = self.__get_values_from_modifier_node_key("include", filter_key, single_key_check=True)
        if filter_value in root_node_key_values or filter_value in include_filter_values:   
            # If the filter_key is present, the query_key will should be
            # and its value is a list
            queried_list[query_key].extend(self.config[query_key])

        # If there is already a list, add any additional value which applies to the whole matrix
        if queried_list[query_key] != []:
            include_values = self.__get_values_from_modifier_node_key("include", query_key, single_key_check=True)
            queried_list[query_key].extend(include_values)
            # Remove duplicates
            queried_list[query_key] = list(set(queried_list[query_key]))
            
        # Add include values matching the filtered key from the include node
        include_values = self.__get_filtered_values_from_modifier_node_key("include", query_key, filter_key, filter_value)
        queried_list[query_key].extend(include_values)
        # Remove duplicates
        queried_list[query_key] = list(set(queried_list[query_key]))

        # Remove exclude values matching the filtered key from the exclude node
        exclude_values = self.__get_filtered_values_from_modifier_node_key("exclude", query_key, filter_key, filter_value)
        # Remove any query value that applies to the whole matrix
        exclude_values.extend(self.__get_values_from_modifier_node_key("exclude", query_key, single_key_check=True))
        exclude_values = list(set(exclude_values))
        queried_list[query_key] = [ item for item in queried_list[query_key] if item not in exclude_values ]

        return queried_list


    def __filtered_query(self, query_key, filter):
        """
        Gets the list of values for the queried key and a filter.
        The filter is a key-value pair. The filter key can be either "fqbn" or "sketch".

        Args:
            - query_key (str): The key to be queried. The allowed keys are "fqbn" and "sketch".
            - filter (str): The filter to be applied. The format should be "key=value".
        
        Returns:
            - queried_list (dict): A dictionary with the queried key and the list of values.
            - If the key is not present in the configuration matrix, an dictionary with an empty list
            will be returned.
        """
        def __validate_filter(filter): 
            # The filter format should be "key=value"
            # Validate the filter format
            if "=" not in filter:
                logging.error(f"Filter \"{filter}\" is not in the format key=value")
                return False
            
            return True
            
        queried_list = { query_key: [] }

        if not __validate_filter(filter):
            return queried_list
            
        filter_key, filter_value = filter.split("=")

        if self.__is_key_valid(filter_key):

            if filter_key == query_key:
                queried_list = self.__query_same_list_and_filter_key(filter_key, filter_value)
            else:
                queried_list = self.__query_diff_list_and_filter_key(query_key, filter_key, filter_value)

        return queried_list


class CiCoreInstaller():
    """
    This class is used to install the Arduino core for the 
    fqbn required in CI.
    """
    def  __init__(self, ci_config):
        """
        Creates the CiCoreInstaller object.

        The ci_config is used to identify which fqnb and
        cores need to be installed when no specific fqbn 
        is provided.
        Args:
            - ci_config (CiCompileMatrix): The configuration matrix object.
        """
        self.ci_config = ci_config

    def install(self, fqbn=None, local=False):
        """
        Installs the core for the fqbn list in the matrix.
        
        Args:
            - fqbn (str): The fqbn to be installed. If not provided, 
            the complete fqbn list in the ci configuration matrix will
            be installed.
        """
        fqbn_list = self.__get_fqbn_list(fqbn)
        for fqbn in fqbn_list:
            if not self.__is_core_installed(fqbn):
                print(f"Installing core for fqbn \"{fqbn}\"")
                self.__install_core(fqbn, local=local)
            else:   
                print(f"Core for fqbn \"{fqbn}\" is already installed.")


    """ Private methods """

    def __get_fqbn_list(self, fqbn=None):
        """
        Gets the list of fqbn.
        If a fqbn is provided, then the list will contain only that fqbn.

        Args:
            - fqbn (str): The fqbn to be installed. If not provided,
        
        Returns:
            - fqbn_list (list): A list of fqbn to be installed.
        """
        if fqbn is None:
            fqbn_list = self.ci_config.get_list("fqbn")
            fqbn_list = fqbn_list["fqbn"]
        else:
            fqbn_list = [fqbn]

        return fqbn_list

    @staticmethod
    def __is_core_installed(fqbn):
        """
        Checks if the core is installed for the provided fqbn.

        It will check if the fqbn is in the list of installed boards,
        using the "arduino-cli board listall" command.

        Args:
            - fqbn (str): The fqbn to be checked.

        Returns:
            - True if the core is installed.
            - False if the core is NOT installed.
        """
        command = [
            "arduino-cli",
            "board",
            "listall",
        ]
        board_list_proc = subprocess.run(command, capture_output=True, text=True, check=False)
        # Check if the fqbn is in the list of installed boards
        if fqbn in board_list_proc.stdout:
            return True

        return False
    
    def __install_core_from_local(self, core):
        """
        Install the core by cloning the repository and using 
        the arduino-devops scripts to build and install it from the local sources.
        This prevents the downloads from the arduino board managers to be polluted 
        by the continuous integration downloads (which are not users download).

        This is only used for the Infineon cores, as they can fulfill the arduino-devops
        scripts requirements for local installation.

        Args:
            - core (str): The core to be installed.
        """
        print("Using local core installation for Infineon cores.")
        # The first part of the url until the /release/ substring will be the repository url
        additional_url = self.ci_config.get_additional_url(core)
        core_repo = additional_url.split("/release")[0] + ".git"

        try: 
            # Clone the repository in a separate repo
            core_build_path = os.path.join(self.ci_config.asset_root_path, "core-build")
            if not os.path.exists(core_build_path):
                os.makedirs(core_build_path)
            subprocess.run(["git", "clone", core_repo, core_build_path], capture_output=True, check=True)

            os.chdir(core_build_path)

            # Move to the latest tag
            subprocess.run(["git", "fetch", "--tags"], capture_output=True, check=True)
            latest_tag = subprocess.run(["git", "describe", "--tags", "--abbrev=0"], capture_output=True, text=True, check=True).stdout.strip()
            subprocess.run(["git", "checkout", latest_tag], capture_output=True, check=True)

            # Install the core from local
            subprocess.run(["python", "../arduino-devops/arduino-packager.py"], capture_output=True, text=True, check=True)
            subprocess.run(["python", "../arduino-devops/pckg-install-local.py", "--pckg-dir", "build"], capture_output=True, text=True, check=True)

            # Remove the core build directory
            os.chdir(self.ci_config.asset_root_path)
            shutil.rmtree(core_build_path)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error installing core from local repository: {e}")
            sys.exit(1)

    def __install_core(self, fqbn, local=False):
        """
        Installs the core for the provided fqbn.
        It will check if the core is a third party core, and if so,
        it will use the additional url provided in the ci config file.
        The core is installed using the "arduino-cli core install" command.

        Args:
            - fqbn (str): The fqbn to be installed.
        
        """
        core = self.__strip_core(fqbn)

        additional_install_flags = []
    
        if local and (core.startswith("infineon") or core.startswith("Infineon")):
            self.__install_core_from_local(core)
        else:
            if self.__is_third_party_core(core):
                additional_install_flags = ["--additional-urls", self.ci_config.get_additional_url(core)]
                if additional_install_flags[1] is None:
                    logging.error(f"Error getting additional url for core \"{core}\"")
                    sys.exit(1)

            command = [
                "arduino-cli",
                "core",
                "install",
                core
            ]

            if additional_install_flags != []:
                command.extend(additional_install_flags)

            core_install_proc = subprocess.run(command, capture_output=True, text=True, check=False)
            if core_install_proc.returncode != 0:
                logging.error(f"Error installing core for fqbn: {fqbn}")
                print(core_install_proc.stderr)
                
        print(f"Core for fqbn \"{fqbn}\" installed successfully.")


    @staticmethod
    def __strip_core(fqbn):
        """
        Strips the core name from the fqbn.
        The core name is the vendor and architecture name.
        The fqbn is in the format <vendor>:<arch>:<board>.
        The core name is in the format <vendor>:<arch>.

        Args:
            - fqbn (str): The fqbn to be stripped.

        Returns:
            - core (str): The core name in the format <vendor>:<arch>.
        """
        try:
            return fqbn.split(":")[0] + ":" + fqbn.split(":")[1]
        except IndexError:
            logging.error(f"Error getting core name from fqbn \"{fqbn}\".\n \
            \rA valid fqbn should be in the format <vendor>:<arch>:<board>.")
            sys.exit(1)

    @staticmethod
    def __is_third_party_core(core):
        """
        Checks if the core is a third party core.
        It will check if the core is searchable using the 
        "arduino-cli core search" command.

        Args:
            - core (str): The core to be checked.
        
        Returns:
            - True if the core is a third party core.
            - False if the core is an Arduino official/built-in core.
        """
        command = [
            "arduino-cli",
            "core",
            "search",
            core,
        ]
        core_search_proc = subprocess.run(command, capture_output=True, text=True, check=False)

        if "No platforms matching your search." in core_search_proc.stdout:
            return True

        return False
        

class LibDepsInstaller():
    """
    This class is used to install the library dependencies for the sketches.
    The library dependencies are installed using the "arduino-cli lib install" command.
    """

    def __init__(self, asset_root_path):
        """
        Creates the LibDepsInstaller object.

        Args:
            - asset_root_path (str): The root path of the asset.
            This is used to find the library dependencies for the sketches.
        """
        self.asset_root_path = asset_root_path

    def install(self):
        """
        Installs the library dependencies for a library asset.
        It inspect the directory for the "library.properties" file,
        and install them using the "arduino-cli lib install" command.
        """

        print("Installing library dependencies...")
        lib_deps = self.__get_lib_deps()
        if lib_deps:
            print(f"Found \"{lib_deps}\" library dependencies to install.")
        else:
            print("No library dependencies found.")
            return

        self.__install_lib(lib_deps)

        print("Library dependencies installed successfully.")

    """ Private methods """

    def __get_lib_deps(self):
        """
        Gets the library dependencies from the library.properties file.

        The file contains a "depends" key with a comma separated list of libraries.
        If the key is empty, it will return an empty list.
        """
        lib_properties_file = os.path.join(self.asset_root_path, "library.properties")
        with open(lib_properties_file, "r") as f:
            lib_properties_content = f.read()

        # Parse the content of the library.properties file and get the "depends" key
        for line in lib_properties_content.splitlines():
            if line.startswith("depends="):
                # The value of the "depends" key is a comma separated list of libraries
                # Remove the "depends=" prefix from the line
                line = line.replace("depends=", "")
                libs = line.strip().split(",")
                return [lib.strip() for lib in libs if lib.strip() != ""]

    @staticmethod
    def __install_lib(libs):
        """
        Installs each of the library of the list passed by argument.

        The library is installed using the "arduino-cli lib install" command.

        Args:
            - libs (list): A list of libraries to be installed.
              The library can as well include the version constraints in the format
              "library (version)"
        """
        def format_lib_arg(lib):
            """
            Formats the library to be used as an argument for the "arduino-cli lib install" command
            in the format:
            "library@version" if the version is specified,
            or just:
            "library" if no version is specified.

            Check the version constraints formats allowed in library.properties file:
            # https://docs.arduino.cc/arduino-cli/library-specification/#version-constraints

            This tool right now only supports constraints which explicitly provide a version.
            Meaning those containing an (at least) equal: >=, <=, =.
            Constraints requiring the discovery of greater, lower or range versions are not (currently) supported.
            """
            # If the lib has a version in parenthesis,
            # the output format will become library@version
            if "(" in lib and ")" in lib:
                lib_name = lib.split("(")[0].strip()

                lib_version = lib.split("(")[1].split(")")[0].strip()
                # Only equal versions will be considered.  No discovery of > or < version will be here implemented.
                if "<=" in lib_version or ">=" in lib_version or "=" in lib_version:
                    lib_version = lib_version.replace("<=", "").replace(">=", "").replace("=", "").strip()

                # Check if this is valid semver version x.y.z. This discard any other not supported constrain.
                if not re.match(r"^\d+\.\d+\.\d+$", lib_version):
                    logging.error(f"Invalid version format for library \"{lib_name}\" : {lib_version}. \n \
                    \rOnly versions constraints \"=, <=, >=\" are implemented.\n \
                    \rNo discovery of greater, lower or range versions in this tool.")
                    sys.exit(1)

                return f"{lib_name}@{lib_version}"
            else:
                return f"{lib}"


        for lib in libs:
            lib_arg = format_lib_arg(lib)
            command = [
                "arduino-cli",
                "lib",
                "install",
                lib_arg,
            ]

            lib_install_proc = subprocess.run(command, capture_output=True, text=True, check=False)

            if lib_install_proc.returncode != 0:
                logging.error(f"Error installing library \"{lib_arg}\"")
                print(lib_install_proc.stderr)
                sys.exit(1)

            print(f"Library \"{lib_arg}\" installed successfully.")

class CiCompileReport:
    """
    Class that generates the compile report for the compile sketches.
    Takes care as well of the the showed format of the results.
    """
    blue_on = "\033[94m"
    green_on = "\033[92m"
    red_on = "\033[91m"
    grey_on = "\033[90m"
    color_off = "\033[0m"

    def __init__(self, fqbn):
        self.pass_list = []
        self.fail_list = []
        self.fqbn = fqbn

    def add_pass(self, sketch):
        self.pass_list.append(sketch)

    def get_pass_len(self):
        return len(self.pass_list)
    
    def add_fail(self, sketch):
        self.fail_list.append(sketch)
    
    def get_fail_len(self):
        return len(self.fail_list)

    def get_total_len(self):
        return len(self.pass_list) + len(self.fail_list)

    def summary(self):
        print(f"{self.blue_on}--------------------------------------------------------{self.color_off}")
        self.__summary_result()
        print(f"{self.blue_on}--------------------------------------------------------{self.color_off}")

    def print_fqbn_header(self):
        print(f"{CiCompileReport.blue_on}--------------------------------------------------------")
        print(f"--> fqbn: {self.fqbn}")
        print(f"--------------------------------------------------------{CiCompileReport.color_off}")

    @staticmethod
    def print_sketch_compile_header(sketch):
        print(f"{CiCompileReport.blue_on}>> {CiCompileReport.color_off}", end="")
        print(f"Compiling \"{sketch}\"", end="", flush=True)

    @staticmethod
    def print_pass_tag():
        print(f"{CiCompileReport.green_on} [PASS] {CiCompileReport.color_off}")
    
    @staticmethod
    def print_fail_tag():
        print(f"{CiCompileReport.red_on} [FAIL] {CiCompileReport.color_off}")

    @staticmethod
    def print_exclude_tag():
        print(f"{CiCompileReport.grey_on} [EXCLUDED] {CiCompileReport.color_off}")

    @staticmethod
    def summary_multiple(reports):
        print(f"\n{CiCompileReport.blue_on}--------------------------------------------------------")
        print("----------- Compile sketches report summary ------------")
        print(f"--------------------------------------------------------{CiCompileReport.color_off}")
        for report in reports:
            print(f"{CiCompileReport.blue_on} - {report.fqbn}{CiCompileReport.color_off} : ", end="")
            report.__summary_result()
        print(f"{CiCompileReport.blue_on}--------------------------------------------------------{CiCompileReport.color_off}")

    """ Private methods """

    def __summary_result(self):
        """
        A different format is used depending if all sketches has failed, all has passed,
        or some has passed and some has failed.
        """
        if self.get_total_len() == self.get_pass_len():
            print(f"All {self.green_on}{self.get_total_len()}{self.color_off} sketches {self.green_on}PASSED{self.color_off}")
        else:
            if self.get_pass_len() > 0:
                print(f"Only {self.green_on}{self.get_pass_len()}{self.color_off} out of {self.blue_on}{self.get_total_len()}{self.color_off} sketches PASSED")

            if self.get_fail_len() > 0:
                if self.get_pass_len() == 0:
                    print(f"All {self.get_total_len()} sketches {self.red_on}FAILED{self.color_off}")
                else:
                    print(f"The following sketches have {self.red_on}FAILED{self.color_off}")
                for sketch in self.fail_list:
                    print(f"   - {sketch}")

class CiCompiler:
    """
    Class to handle the ci matrix of fqbn-sketch compilation and result display. 
    """

    def __init__(self, ci_config):
        """
        The constructor creates the CiCompiler object.
        The ci_config is used to access the fqbn-sketch matrix and the sketches 
        to be compiled against the fqbn list.

        Args:
            - ci_config (CiCompileMatrix): The configuration matrix object.
        """
        self.ci_config = ci_config
        self.compile_reports = [] 

    def compile(self, fqbn=None, sketch=None):
        """
        Compiles the sketches for the fqbn list in the matrix.
        If a fqbn is provided, then only that fqbn will be compiled.
        If a sketch is provided, then only that sketch will be compiled.
        If no fqbn or sketch is provided, then the complete matrix will be compiled.
        The sketches are compiled using the "arduino-cli compile" command.

        If any of the sketches fails to compile, the script will exit with code 1.

        Args:
            - fqbn (str): The fqbn to be compiled. If not provided, 
            the complete fqbn list in the ci configuration matrix will
            be compiled.
            - sketch (str): The sketch to be compiled. If not provided,
            the complete sketch list in the ci configuration matrix will
            be compiled.
        """

        fqbn_list = self.__get_fqbn_list(fqbn)
        for fqbn in fqbn_list:
            
            fqbn_report = CiCompileReport(fqbn)
            self.compile_reports.append(fqbn_report)
            fqbn_report.print_fqbn_header()

            
            fqbn_sketch_list = self.__get_sketch_file_list(fqbn, sketch)
            all_sketch_list = self.__get_sketch_file_list_no_dirs(self.ci_config.get_list("sketch")["sketch"])
            
            for sketch_file in all_sketch_list:
                # Report this sketch is excluded 
                if sketch_file not in fqbn_sketch_list:
                    CiCompileReport.print_sketch_compile_header(sketch_file)
                    CiCompileReport.print_exclude_tag()
                    continue

                self.__compile_sketch(fqbn, sketch_file, fqbn_report)

            fqbn_report.summary()

        # Only multiple fqbn are compiled, create a summary report
        if len(self.compile_reports) > 1:
            CiCompileReport.summary_multiple(self.compile_reports)

        for report in self.compile_reports:
            if report.get_fail_len() > 0:
                sys.exit(1)

    """ Private methods """

    def __get_fqbn_list(self, fqbn=None):
        """
        Gets the list of fqbn.
        If a fqbn is provided, then the list will contain only that fqbn.

        Args:
            - fqbn (str): The fqbn to be installed. If not provided,
        
        Returns:
            - fqbn_list (list): A list of fqbn to be installed.
        """
        if fqbn is None:
            fqbn_list = self.ci_config.get_list("fqbn")
            fqbn_list = fqbn_list["fqbn"]
        else:
            fqbn_list = [fqbn]

        return fqbn_list

    def __get_sketch_file_list_no_dirs(self, sketch_list):
        """
        Get the list of sketches for a given sketch list.
        If a sketch is not a .ino file, then it is a directory containing
        .ino files. Discover all the .ino files in the directory and
        add them to the sketch list, and remove the directory from the list.

        Args:
            - sketch_list (list): The list of sketches to be processed.
        
        Returns:
            - sketch_list (list): The list of sketches with all the .ino files
            discovered in the directories.
        """
        remove_dirs = []
        for sketch in sketch_list:
            if os.path.isdir(sketch):
                # Get all the .ino files in the directory
                sketch_dir = os.path.join(self.ci_config.asset_root_path, sketch)
                if not os.path.exists(sketch_dir):
                    logging.error(f"Sketch directory \"{sketch_dir}\" not found")
                    sys.exit(1)
                for root, dirs, files in os.walk(sketch_dir):
                    for file in files:
                        if file.endswith(".ino"):
                            sketch_with_full_path = os.path.join(root, file)
                            sketch_with_relative_path = os.path.relpath(sketch_with_full_path, self.ci_config.asset_root_path)
                            sketch_list.append(sketch_with_relative_path)
                # Add the directory to the remove list
                remove_dirs.append(sketch)

        # Remove the directories from the list
        for sketch in remove_dirs:
            sketch_list.remove(sketch)
        
        return sketch_list

    def __get_sketch_file_list(self, fqbn, sketch=None):
        """
        Get the list of sketches for a given fqbn.
        If a sketch is provided, then the list will contain only that sketch.

        Args:
            - fqbn (str): The fqbn to filter only its relevant sketches.
            - sketch (str): The sketch to be compiled. If not provided,
            the complete sketch list in the ci configuration matrix will
            be compiled.
        
        Returns:
            - sketch_list (list): A list of sketches to be compiled.
        """
        if sketch is None:
            sketch_list = self.ci_config.get_list("sketch","fqbn=" + fqbn)
            sketch_list = sketch_list["sketch"]
        else:
            sketch_list = [sketch]
    
        sketch_list = self.__get_sketch_file_list_no_dirs(sketch_list)

        return sketch_list
    
    def __compile_sketch(self, fqbn, sketch, compile_report):
        """
        Compiles the sketch for the given fqbn.
        The sketch is compiled using the "arduino-cli compile" command.
        If the asset type is a library, the "--library" flag is added to the command.

        Args:
            - fqbn (str): The fqbn to be compiled.
            - sketch (str): The sketch to be compiled.
            - compile_report (CiCompileReport): The compile report object.
        """
        command = [
            "arduino-cli",
            "compile",
            "--fqbn",
            fqbn,
            sketch,
        ]

        library_flags = ""
        if self.ci_config.asset_type == "library":
            library_flags = ["--library", "."]

        if library_flags != "":
            command.extend(library_flags)

        CiCompileReport.print_sketch_compile_header(sketch)
        compile_proc = subprocess.run(command, capture_output=True, text=True, check=False)

        if compile_proc.returncode != 0:
            CiCompileReport.print_fail_tag()
            print(compile_proc.stderr)
            compile_report.add_fail(sketch)
        else:
            CiCompileReport.print_pass_tag()
            # TODO: Implement a proper logging system
            # if args.verbose:
            #     print(compile_proc.stdout)
            compile_report.add_pass(sketch)


class CiParser:
    """
    Class that parses the ci tool arguments
    """

    def __init__(self):
        """
        The constructor creates the argument parser and parses the arguments.
        """
        # Get the script name without .py extension
        self.ci_tool_name = os.path.splitext(os.path.basename(__file__))[0]
        self.ci_tool_version = "0.3.0"
        self.__create_parser()

        args = self.parser.parse_args(namespace=argparse.Namespace(ci_parser=self))
        args.func(args)

        """ Private class methods """

    class __ver_action(argparse.Action):
        def __init__(self, option_strings, dest, **kwargs):
            super().__init__(
                option_strings, dest, nargs=0, default=argparse.SUPPRESS, **kwargs
            )

        def __call__(self, parser, namespace, values, option_string=None):
            # Retrieve the package_parser object from the namespace
            ci_parser = getattr(namespace, "ci_parser", None)
            print(
                ci_parser.ci_tool_name
                + " version: "
                + ci_parser.ci_tool_version
            )
            parser.exit()
    
    def __main_parser_func(self, args):
        """
        Main parser function of arduino CI cli tool
        """
        self.parser.print_help()

    def __get_ci_config(self, args):
        """
        Get ci configuration instance
        If no configuration file is provided,
        it will use the default configuration file
        in the root path of the asset.
        """
        if args.ci_matrix_yml is None:
            args.ci_matrix_yml = os.path.join(args.root_path, "ci-matrix-config.yml")

        if args.verbose:
            logging.getLogger().setLevel(logging.INFO)

            print(f"Arduino asset root path:      {args.root_path}")
            print(f"CI matrix configuration file: {args.ci_matrix_yml}")

        ci_config = CiMatrixConfig(args.ci_matrix_yml, args.root_path)

        return ci_config
    
    def __config_parser_func(self, args):
        """
        Config parser function of arduino CI cli tool
        """
        def get_queried_config(ci_config, args):
            if args.list is not None:
                queried_config = ci_config.get_list(args.list, args.filter)
            else:
                if args.filter is not None:
                    logging.error(f"The filter option is only available for the list command.")
                    sys.exit(1)
                
                queried_config = ci_config.config
        
            return queried_config

        def print_config(queried_config, args):
            if args.json_pretty:
                print(json.dumps(queried_config, indent=4))  
            elif args.yaml:
                print(yaml.dump(queried_config, indent=4, default_flow_style=False))
            else:
                print(queried_config)

        ci_config = self.__get_ci_config(args)
        queried_config = get_queried_config(ci_config, args)
        print_config(queried_config, args)
        
    def __compile_parser_func(self, args):
        """
        Compile parser function of arduino CI cli tool
        """
        ci_config = self.__get_ci_config(args)
        ci_compiler = CiCompiler(ci_config)
        ci_compiler.compile(args.fqbn, args.sketch)

    def __core_install_parser_func(self, args):
        """
        Core install parser function of arduino CI cli tool
        """
        ci_config = self.__get_ci_config(args)
        ci_core_installer = CiCoreInstaller(ci_config)
        ci_core_installer.install(args.fqbn, args.local)

    def __lib_deps_install_parser_func(self, args):
        """
        Library deps install parser function of arduino CI cli tool
        """
        lib_deps_installer = LibDepsInstaller(args.root_path)
        lib_deps_installer.install()

    def __create_parser(self):
        """
        Creates the argument parser for the build CI matrix script.
        """
        def add_shared_args(parser):
            # Argument for ci matrix yaml file
            parser.add_argument(
                "-c",
                "--ci-matrix-yml",
                type=str,
                default=None,
                help='The path to the ci matrix configuration yml file. Default for libraries is different than for cores.',
            )

            # Argument for asset (core or library) root path
            parser.add_argument(
                "-r",
                "--root-path",
                type=str,
                default=os.getcwd(),
                help="Path to the arduino asset (library or core) root directory. Default is the current directory",
            )

            # Argument for verbose output
            parser.add_argument(
                "--verbose",
                action="store_true",
                default=False,
                help="Verbose output",
            )

        self.parser = argparse.ArgumentParser(
            description="CI utility for Arduino assets",
        )

        # Argument for version
        self.parser.add_argument(
            "-v",
            "--version",
            action=self.__ver_action,
            help=self.ci_tool_name + " version",
        )

        # Set the main parser function
        self.parser.set_defaults(func=self.__main_parser_func)
        add_shared_args(self.parser)

        # Add subparsers 
        subparsers = self.parser.add_subparsers()

        # Add the config subparser
        config_parser = subparsers.add_parser(
            "config",
            help="CI configuration matrix",
        )
        config_parser.set_defaults(func=self.__config_parser_func)
        add_shared_args(config_parser)

        config_exclusive_group = config_parser.add_mutually_exclusive_group(required=False)

        # Argument for json pretty output
        config_exclusive_group.add_argument(
            "--json-pretty",
            action="store_true",
            default=False,
          help="Output the configuration in JSON format",
        )
        
        # Argument for yaml output
        config_exclusive_group.add_argument(
            "--yaml",
            action="store_true",
            default=False,
            help="Output the configuration in YAML format",
        )

        # Argument for query list
        config_parser.add_argument(
            "--list",
            type=str,
            default=None,
            help="List all the elements of a given key in the configuration matrix",
        )

        # Argument for filtering the query list
        config_parser.add_argument(
            "--filter",
            type=str,
            default=None,
            help="Filter the list of elements based on a give the value of another key",
        )

        # Add the compile subparser
        compile_parser = subparsers.add_parser(
            "compile",
            help="Compile the ci matrix sketches for the fqbn matrix list or for a given fqbn",
        )
        compile_parser.set_defaults(func=self.__compile_parser_func)
        add_shared_args(compile_parser)

        # Argument for the compiled fqbn
        compile_parser.add_argument(
            "--fqbn",
            type=str,
            default=None,
            help="The fqbn of the board to user for compilation",
        )

        # Argument for the compiled sketch
        compile_parser.add_argument(
            "--sketch",
            type=str,
            default=None,
            help="The sketch to be compiled",
        )

        # Add the core-install subparser
        core_install_parser = subparsers.add_parser(
            "core-install",
            help="Install the core for the fqbn matrix list or for a given fqbn",
        )
        core_install_parser.set_defaults(func=self.__core_install_parser_func)
        add_shared_args(core_install_parser)

        # Argument for the compiled fqbn
        core_install_parser.add_argument(
            "--fqbn",
            type=str,
            default=None,
            help="The fqbn of the board to be installed",
        )

        # Argument for installing Infineon core from repo (instead of from releases)
        core_install_parser.add_argument(
            "--local",
            action="store_true",
            default=True,
            help="Install the core from local repository if available. This is only for Infineon cores.",
        )

        # Add the lib-deps-install subparser
        lib_deps_install_parser = subparsers.add_parser(
            "lib-deps-install",
            help="Install the \"depends\" libraries in the  \"library.properties\" file of the library asset",
        )
        lib_deps_install_parser.set_defaults(func=self.__lib_deps_install_parser_func)
        add_shared_args(lib_deps_install_parser)


if __name__ == "__main__":

    ci_parser = CiParser()