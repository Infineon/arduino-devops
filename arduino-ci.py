import argparse
import json
import logging
import os
import sys
import subprocess
import yaml

# Create logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

class CiMatrixConfig:
    """
    Class to parse the CI compile sketches configuration file

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
                "ifx-lib-dflt-ci-config-matrix.yml" provided in this repository.
            
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
                    - fqbn: vendor:avr:board        # The value of this key can be a scalar or list
                      sketch:                       # The value of this key can be a scalar or list
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
                    - fqbn: vendor:avr:board        # The value of this key can be a scalar or list
                      sketch:                       # The value of this key can be a scalar or list
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
    """
    def __init__(self, ci_matrix_yml, asset_root_path):
        """
        Constructor of the CI compile matrix configuration class.

        The ci matrix yaml file is parsed and the configuration is 
        stored in a dictionary.
        The ci matrix file is optional (for cores). If the file is not present, 
        or if values for they main keys "fqbn" and/or "sketch", these
        will be discovered automatically.

        The asset type is also discovered automatically based on:
            - For libraries, the "sketch" list will be searched in the "examples" folder.
            The "fqbn list needs to be provided. Therefore, at least the yml file,
            with the set of "fqbn" is required for libraries.

            - For cores, the directory to search for the "sketch" list is "libraries".
            The "fqnb" list is extracted from the "boards.txt" file.

        Additionally, if not specified, the asset type is also automatically detected. 
        The asset type can be either a library or a core. A library is considered when
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
        return str(self.config)
    
    def __str__as_json_pretty(self):
        """Uses json dump to generate a pretty string"""
        return json.dumps(self.config, indent=4)

    def get_list(self, query_key, filter=None):
        """
        List all the elements of a given key ("fqbn" or "sketch") in the configuration matrix.
        If filter is provided, it will filter the list based on the value of another key.

        Args:
            - query_key (str): The key to be queried. The allowed keys are "fqbn" and "sketch".
            - filter (str): The filter to be applied. The format should be "key=value".

        Returns:
            - queried_list (dict): A dictionary with the queried key and the list of values.
            - If the key is not present in the configuration matrix, an directory with an empty list
            will be returned.
        """

        logging.info(f"Querying the configuration matrix for key \"{query_key}\" and filter \"{filter}\"")

        queried_list = { query_key: [] }

        if self.__is_key_valid(query_key):
            
            if filter is None:
                queried_list = self.__query(query_key)
            else:
                queried_list = self.__filtered_query(query_key, filter)

        
        queried_list[query_key] = sorted(queried_list[query_key], key=str.lower)
        
        return queried_list
        
    """ Private methods """

    def __parse_config(self):
        """Parses the matrix ci yml file"""
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

        def library_fqbn_list_default():
            return [] # This will be the default values chosen by Julian. If not added by the library, the arduino-devops can provide one.
        
        def core_fqbn_list_auto_discovery():

            fqbn_list = []
                    
            boards_txt = os.path.exists(os.path.join(self.asset_root_path, "boards.txt"))
            if not boards_txt:
                logging.error(f"\"boards.txt\" file not found in the asset root path \"{self.asset_root_path}\"")
                sys.exit(1)
            
            # Load content of boards.txt file
            with open(os.path.join(self.asset_root_path, "boards.txt"), "r") as f:
                boards_txt_content = f.read()

            # look for the lines with pattern <prefix>.name=<board_name> and
            # extract the prefix in board_txt_content
            # The prefix is the fqbn
   
            board_name_list = []
            for line in boards_txt_content.splitlines():
                if line.startswith("#") or line.strip() == "":
                    continue
                if ".name=" in line:
                    prefix = line.split(".name=")[0].strip()
                    if prefix not in board_name_list:
                        board_name_list.append(prefix)
                        logging.info(f"Found fqbn: \"{prefix}\"")

            # remove duplicates
            board_name_list = list(set(board_name_list))

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

            for board in board_name_list:
                fqbn = f"{vendor_name}:{arch_name}:{board}"
                fqbn_list.append(fqbn)
                logging.info(f"Found fqbn: \"{fqbn}\"")

            return fqbn_list

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

        def sketch_list_auto_discovery(sketch_path_list):
            sketch_list = []

            for sketch_path in sketch_path_list:
                # The default search path is the "sketch" folder
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
                            sketch_list.append(sketch_with_relative_path)
                            logging.info(f"Found sketch: \"{sketch_with_relative_path}\"")

        
            return sketch_list

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
        Discover the asset type based on the root path.
        The asset type can be either a library or a core.
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
        """
        
        logging.info(f"Validating key: \"{key}\"")
        
        allowed_list_keys = ["fqbn", "sketch"]

        if key not in allowed_list_keys:
            logging.error(f"Key \"{key}\" is not allowed. Allowed keys are: \"{allowed_list_keys}\"")
            return False

        key_in_config = False
        if key in self.config:
            logging.info(f"Key \"{key}\" found in the configuration matrix")
            key_in_config = True
        else:
            if "include" in self.config:
                for entry in self.config["include"]:
                    if key in entry:
                        logging.info(f"Key \"{key}\" found in \"include\" list")
                        key_in_config = True
                        break
        
        if not key_in_config:
            logging.error(f"Key \"{key}\" not found in the configuration matrix")
            return False

        return True

    def __get_values_from_root_node_key(self, key):
        values = []

        if key in self.config:
            # This should be always a list # TODO: Add validation in separate method.
            values = self.config[key]

        return values

    def __get_values_from_modifier_node_key(self, node, key, single_key_check=False):
        
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
        It will return the list of values for the queried key.
        The key is present at least in:
            - As main node key of the default configuration matrix
            - As part of the "include" key
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
        If the filter key is the same as the list, the user is
        querying if the value is present in the configuration in 
        the main matrix or in the include/exclude.
        """
        queried_list = { query_filter_key: [] }

        queried_key_values = self.__query(query_filter_key)
        if filter_value in queried_key_values[query_filter_key]:
            queried_list[query_filter_key] = [ filter_value ]

        return queried_list
            
    def __query_diff_list_and_filter_key(self, query_key, filter_key, filter_value):

        queried_list = { query_key: [] }

        root_node_key_values = self.__get_values_from_root_node_key(filter_key)
        if filter_value in root_node_key_values:   
            # If the filter_key is present, the query_key will should be
            # and its value is a list
            queried_list[query_key].extend(self.config[query_key])

        # If there is already a base list, add any additional value which applies to the whole matrix
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
        It will return the list of values for the queried key and a filter.
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
        logging.info(f"Filtering for key \"{filter_key}\" with value \"{filter_value}\"")

        if self.__is_key_valid(filter_key):

            if filter_key == query_key:
                queried_list = self.__query_same_list_and_filter_key(filter_key, filter_value)
            else:
                queried_list = self.__query_diff_list_and_filter_key(query_key, filter_key, filter_value)

        return queried_list

class CiCompileReport:
    def __init__(self):
        self.pass_list = []
        self.fail_list = []

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
        print("\033[94m--------------------------------------------------------")
        print("----------- Compile sketches report summary ------------")
        print("--------------------------------------------------------\033[0m")

        if self.get_total_len() == self.get_pass_len():
            print(f"All \033[92m{self.get_total_len()}\033[0m sketches \033[92mPASSED\033[0m !! :) ")
        else:
            if self.get_pass_len() > 0:
                print(f"Only \033[92m{self.get_pass_len()}\033[0m out of \033[94m{self.get_total_len()}\033[0m sketches PASSED")

            if self.get_fail_len() > 0:
                if self.get_pass_len() == 0:
                    print(f"All {self.get_total_len()} sketches \033[91mFAILED\033[0m")
                else:
                    print(f"The following sketches have \033[91mFAILED\033[0m")
                for sketch in self.fail_list:
                    print(f"   - {sketch}")

        print("\033[94m--------------------------------------------------------\033[0m")

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
        self.ci_tool_version = "0.1.0"
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
        if args.ci_matrix_yml is None:
            args.ci_matrix_yml = os.path.join(args.root_path, "ci-matrix-config.yml")

        if args.verbose:
            # Enable logging info
            logging.getLogger().setLevel(logging.INFO)

            print(f"Arduino asset root path:      {args.root_path}")
            print(f"CI matrix configuration file: {args.ci_matrix_yml}")

        ci_config = CiMatrixConfig(args.ci_matrix_yml, args.root_path)

        return ci_config
    
    def __config_parser_func(self, args):

        ci_config = self.__main_parser_func(args)

        if args.list is not None:
            queried_config = ci_config.get_list(args.list, args.filter)
        else:
            if args.filter is not None:
                logging.error(f"The filter option is only available for the list command.")
                sys.exit(1)
            
            queried_config = ci_config.config

        # Print with desired format
        if args.json_pretty:
            print(json.dumps(queried_config, indent=4))  
        elif args.yaml:
            print(yaml.dump(queried_config, indent=4, default_flow_style=False))
        else:
            print(queried_config)

    def __compile_parser_func(self, args):

        def get_sketch_list(self, args, fqbn):
            """
            Get the list of sketches for a given fqbn.
            If a sketch is not provided, then it will get the list
            from the configuration matrix file.
            """
            if args.sketch is None:
                ci_config = self.__main_parser_func(args)
                sketch_list = ci_config.get_list("sketch","fqbn=" + fqbn)
                sketch_list = sketch_list["sketch"]
            else:
                sketch_list = [args.sketch]
        
            # Iterate over the sketch list. If the 
            # the sketch is not a .ino file, then it is a directory containing
            # .ino files. Discover all the .ino files in the directory and 
            # add them to the sketch list, and remove the directory from the list.
            remove_dirs = []
            for sketch in sketch_list:
                if os.path.isdir(sketch):
                    # Get all the .ino files in the directory
                    sketch_dir = os.path.join(args.root_path, sketch)
                    if not os.path.exists(sketch_dir):
                        logging.error(f"Sketch directory \"{sketch_dir}\" not found")
                        sys.exit(1)
                    for root, dirs, files in os.walk(sketch_dir):
                        for file in files:
                            if file.endswith(".ino"):
                                sketch_with_full_path = os.path.join(root, file)
                                sketch_with_relative_path = os.path.relpath(sketch_with_full_path, args.root_path)
                                sketch_list.append(sketch_with_relative_path)
                    # Remove the directory from the list
                    remove_dirs.append(sketch)

            # Remove the directories from the list
            for sketch in remove_dirs:
                sketch_list.remove(sketch)

            return sketch_list

        def get_fqbn_list(self, args):
            """
            Get the list of fqbn for a given sketch.
            If a fqbn is not provided, then it will get the list
            from the configuration matrix file.
            """
            if args.fqbn is None:
                ci_config = self.__main_parser_func(args)
                fqbn_list = ci_config.get_list("fqbn")
                fqbn_list = fqbn_list["fqbn"]
            else:
                fqbn_list = [args.fqbn]

            return fqbn_list


        compile_report = CiCompileReport()

        fqbn_list = get_fqbn_list(self, args)

        for fqbn in fqbn_list:
            print("\n\033[94m--------------------------------------------------------")
            print(f"--> fqbn: {fqbn}")
            print("--------------------------------------------------------\033[0m")
            sketch_list = get_sketch_list(self, args, fqbn)
            for sketch in sketch_list:
                command = [
                    "arduino-cli",
                    "compile",
                    "--fqbn",
                    fqbn,
                    sketch
                ]

                print("\033[94m>> \033[0m", end="")
                print(f"Compiling \"{sketch}\"", end="", flush=True)
                compile_proc = subprocess.run(command, capture_output=True, text=True, check=False)

                if compile_proc.returncode != 0:
                    print("\033[91m [FAIL] \033[0m")
                    print(compile_proc.stderr)
                    compile_report.add_fail(sketch)
                else:
                    print("\033[92m [PASS] \033[0m")
                    if args.verbose:
                        print(compile_proc.stdout)
                    compile_report.add_pass(sketch)

            compile_report.summary()
            if compile_report.get_fail_len() > 0:
                sys.exit(1)

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

        # Add the config subparser
        compile_parser = subparsers.add_parser(
            "compile",
            help="Compile the ci matrix sketches for a given fqbn",
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


if __name__ == "__main__":

    ci_parser = CiParser()