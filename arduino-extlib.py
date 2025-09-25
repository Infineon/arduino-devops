import argparse
import os
import yaml
import logging
import shutil
import subprocess
import filecmp
import sys

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

class ExtLib:
    """
    Class to handle external library submodule management based on the
    .extlib.yml configuration file.
    This configuration file contains the following key-value pairs:

    - repo: Path to the external library submodule (relative to the root path)
    - tag: Git tag of the external library submodule (automatically updated when mode is set to copy)
    - head: Git hash of the external library submodule (automatically updated when mode is set to copy)
    - files: List of files or directories to be linked or copied from the submodule to the destination
      - dest: Destination path relative to the root path
      - src: Source file or directory path relative to the submodule path
    - mode: Mode of operation, either "symlink" or "copy" (automatically updated when mode is set)

    An example of this file is as follows:

        - repo: extras/libfoo
          tag: v1.2.3
          head: fa3b2c1d4e5f67890123456789abcdef12345678
          files:        
            dest: src/libfoo
            src: src
          mode: copy

    The file allows a list of such entries to manage multiple external libraries.
    Also, it allows multiple files dictionaries in the files entry.


    When using the "symlink" mode, the specified files or directories are symlinked
    from the submodule to the destination. This is useful during development as it
    allows changes in the submodule to be immediately reflected in the destination.

    In that case, the ".extlib.yml" file is updated to set the mode to "symlink"
    and the tag and head values are set to "unset".
    It will look like this:

        - repo: extras/libfoo
          tag: unset
          head: unset
          files:
            dest: src/libfoo
            src: src
          mode: symlinks
    """
    def __init__(self, extlib_yml, asset_root_path):
        """
        Constructor of the external lib config class.

        Args:
            extlib_yml (str): Path to the .extlib.yml configuration file.
            asset_root_path (str): Root path of the library where the submodules are located.
        """
        self.extlib_yml = extlib_yml
        self.asset_root_path = asset_root_path

        self.config = self.__parse_config()
       
    def set_mode(self, submodule, mode):
        """
        Sets the mode for the external library.

        Args:
            submodule (str): Name of the external library submodule. Including path (i.e.) "extras/libfoo".
                             If None, all submodules will be processed.
            mode (str): Mode to set for the external library submodule. Either "symlink" or "copy".
        """
        
        submodule_list = self.__get_submodules(submodule)

        for repo in submodule_list:
            
            self.__udpate_config_yml(repo, f"pre-{mode}")
            self.__set_dest(repo)
            self.__sync_files(repo, mode)
            self.__udpate_config_yml(repo, mode)

    def verify(self, submodule = None):
        """
        Verifies that the copied versions match the library submodule version.

        Args:
            submodule (str): Name of the external library submodule. Including path (i.e.) "extras/libfoo".
                             If None, all submodules will be processed.
        """
        submodule_list = self.__get_submodules(submodule)
    
        for repo in submodule_list:
            if repo.get("mode") != "copy":
                continue
            
            # Check if the source git tag and hash match the .extlib.yml file values
            if repo.get("tag") != self.__get_git_tag(repo):
              logging.error(f"The submodule \"{repo.get('repo')}\" tag and extlib metafile version does not match.")
              logging.error(f"Submodule tag: {self.__get_git_tag(repo)}")
              logging.error(f"extlib.yml tag: {repo.get('tag')}") 
              sys.exit(1)

            if repo.get("head") != self.__get_git_hash(repo):
               logging.error(f"The submodule \"{repo.get('repo')}\" head and extlib metafile head does not match.")
               logging.error(f"Submodule head: {self.__get_git_hash(repo)}")
               logging.error(f"extlib.yml head: {repo.get('head')}")
               sys.exit(1)

            # Even if the metafile and the submodule match 
            # we check if actually the copied files match the submodule files
            files = repo.get("files", [])
            if isinstance(repo.get("files", []), dict):
                    files = [repo["files"]]
            
            for file in files:
                src_path = os.path.join(self.asset_root_path, repo.get("repo"), file.get("src", []))
                dest_path = os.path.join(self.asset_root_path, file.get("dest", []))
                git_diff_result = self.__get_git_diff(src_path, dest_path)
                if  git_diff_result != "":
                    logging.error(git_diff_result)
                    sys.exit(1)

    def __parse_config(self):
        """
        Parses the config yml file and returns the config as a dictionary.

        Returns:
            dict: Configuration dictionary.
        """
        config = {}
        try:
            with open(self.extlib_yml, "r") as f:
                config = yaml.safe_load(f)
                if config is None:
                    config = {}
        except FileNotFoundError:
            logging.error("No extlib.yml file found at %s", self.extlib_yml)

        return config
    
    def __get_submodules(self, submodule = None):
        """
        Returns the requested submodule passed by argument.
        If no submodule is passed, returns all submodules.

        Args:
            submodule (str): Name of the external library submodule. Including path (i.e.) "extras/libfoo".
                             If None, all submodules will be processed.
        Returns: 
            list of submodules
        """

        # The configuration can be a single library entry 
        # or a list of them
        if isinstance(self.config, dict):
            self.config = [self.config]
        
        if submodule is None: 
            # Return all submodules
            return self.config
        else:
            queried_submodule = []
            for entry in self.config:
                if entry.get("repo") == submodule:
                    queried_submodule.append(entry)
                    return queried_submodule
            
            if queried_submodule == []:
                logging.error(f"Submodule {submodule} not found in the configuration.")
                return []
            
    '''
    # TODO: To evaluate in future. 
    # Do we need to enable the usage of wildcard and file patterns?
    # In principle is easy to do, but then we have to discriminate 
    # in the destinations which files are relevant to keep and which need to be deleted
    # based on the current head content...
    # For example, if they have also been deleted in the source from a previous copied version.
    # Useful, but will keep also this script more complex than required. 

    def __set_src(self, submodule = None):
        submodule_list = self.__get_submodules(submodule)

        expanded_repo_file_list = []
        for repo in submodule_list:
            files = repo.get("files", {})

            # A file can be a single dictionary
            # or a list of dictionaries
            if isinstance(files, dict):
                files = [files]

            # New file list with the expanded src list
            expanded_file_list = []

            for file in files:
                expanded_file = {"dest": file.get("dest", []), "src": []}

                src_list = file.get("src", [])

                # The src be a single string or a list
                # of strings. Convert to list if needed
                if isinstance(src_list, str):
                    src_list = [src_list]
        
                for src in src_list:
                    # Expand any in the src list
                    if '*' in src:
                        src_with_path = os.path.join(self.asset_root_path, repo.get("repo"), src)
                        src = glob.glob(src_with_path)
                        # Remove path from src
                        src = [os.path.relpath(s, os.path.join(self.asset_root_path, repo.get("repo"))) for s in src]     
                        expanded_file["src"].extend(src)
                    # No expansion needed otherwise
                    else:
                        expanded_file["src"].append(src)
                
                expanded_file_list.append(expanded_file)
            
            expanded_repo_file_list.append({ "repo": repo.get("repo"), "files": expanded_file_list })
        
        return expanded_repo_file_list
    '''

    def __set_dest(self, submodule):
        """
        Creates the files destination directories if they do not exist.

        Args:
            submodule (dict): Submodule configuration dictionary.
        """
        file_list = submodule.get("files", [])
        if isinstance(file_list, dict):
            file_list = [file_list]

        for file in file_list:
            dest_path = os.path.join(self.asset_root_path, file.get("dest"))
            
            if os.path.exists(dest_path) or os.path.islink(dest_path):
                logging.warning(f"Destination path {dest_path} already exists. Removing existing directory.")
                if os.path.isdir(dest_path) and not os.path.islink(dest_path):
                    shutil.rmtree(dest_path)
                else:
                    os.remove(dest_path)

    def __sync_files(self, submodule, mode):
        """
        Syncs the files from the submodule to the destination based on the mode.
        
        Args:
            submodule (dict): Submodule configuration dictionary.
            mode (str): Mode to set for the external library submodule. Either "symlink or "copy".
        """
        def link(src ,dest):
            try:
                os.symlink(src, dest)
            except OSError as e:
                logging.error(f"Failed to create symlink: {e}")

        def copy(src, dest):
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                
                if os.path.isdir(src):
                    if os.path.exists(dest):
                        shutil.rmtree(dest)
                    shutil.copytree(src, dest)
                else:
                    shutil.copy2(src, dest)
                    
            except (OSError, shutil.Error) as e:
                logging.error(f"Failed to copy {src} to {dest}: {e}")

        def set_sync_func(mode):
            if mode == 'symlink':
                return link
            elif mode == 'copy':
                return copy
            else:
                raise ValueError(f"Unsupported mode: {mode}")

        file_list = submodule.get("files", [])
        # A file can be a single dictionary
        # or a list of dictionaries
        if isinstance(file_list, dict):
            file_list = [file_list]

        for file in file_list:
            src_list = file.get("src", [])
            # The src can be a single string or a list
            if isinstance(src_list, str):
                src_list = [src_list]

            dest_path = os.path.join(self.asset_root_path, file.get("dest"))
            for src in src_list:
                src_path = os.path.join(self.asset_root_path, submodule.get("repo"), src)
                sync_func = set_sync_func(mode)
                sync_func(src_path, dest_path)

    def __get_git_tag(self, submodule):
        """
        Gets git tag of the submodule

        Args:
            submodule (dict): Submodule configuration dictionary.
        
        Returns:
            str: Git tag of the submodule.
        """  
        command = ["git", "-C", os.path.join(self.asset_root_path, submodule.get("repo")), "describe", "--tags", "--dirty"]
        git_tag = subprocess.run(command, capture_output=True, text=True, check=False)
        git_tag_result = git_tag.stdout.strip()

        return git_tag_result 

    def __get_git_hash(self, submodule):
        """
        Gets git hash of the submodule

        Args:
            submodule (dict): Submodule configuration dictionary.

        Returns:
            str: Git hash of the submodule, with "-dirty" suffix if there are uncommitted changes.
        """  
        hash_command = ["git", "-C", os.path.join(self.asset_root_path, submodule.get("repo")), "rev-parse", "HEAD"]
        git_hash = subprocess.run(hash_command, capture_output=True, text=True, check=False)
        hash_result = git_hash.stdout.strip()

        # Check if dirty
        status_command = ["git", "-C", os.path.join(self.asset_root_path, submodule.get("repo")), "status", "--porcelain"]
        status_result = subprocess.run(status_command, capture_output=True, text=True, check=False)
    
        if status_result.stdout.strip():
            return f"{hash_result}-dirty"
        else:
            return hash_result
        
    def __get_git_diff(self, src_path, dest_path):
        """
        Gets git diff of the submodule between src_path and dest_path

        Args:
            submodule (dict): Submodule configuration dictionary.
            src_path (str): Source path to compare.
            dest_path (str): Destination path to compare.

        Returns:
            str: Git diff output.
        """  
        command = ["git", "-C", self.asset_root_path, "diff", "--no-index", src_path, dest_path]
        git_diff = subprocess.run(command, capture_output=True, text=True, check=False)
        git_diff_result = git_diff.stdout.strip()

        # An error unrelated to identical or different
        if git_diff.returncode not in [0, 1]: 
            logging.error(f"Git diff command failed with error: {git_diff.stderr.strip()}")
            return None

        return git_diff_result

    def __udpate_config_yml(self, submodule, mode):
        """
        Updates the .extlib.yml file with the new mode and, if mode is copy,
        updates the tag and head values with the current git tag and hash of the submodule.

        Args:
            submodule (dict): Submodule configuration dictionary.
            mode (str): Mode to set for the external library submodule. Either "symlink or "copy".
        """

        submodule["mode"] = mode
        if mode == "pre-symlink" or mode == "pre-copy" or mode == "symlink":
            submodule["head"] = "unset"
            submodule["tag"] = "unset"
        elif mode == "copy":
            submodule["head"] = self.__get_git_hash(submodule)
            submodule["tag"] = self.__get_git_tag(submodule)

        with open(self.extlib_yml, "w") as f:
            yaml.dump(self.config, f, indent=2, sort_keys=False)

    def str__as_yml(self):
        """Uses yaml dump to generate a string"""
        return yaml.dump(self.config, indent=4, default_flow_style=False)


class ExtlibParser:
    """
    Class that parses the extlib command line arguments
    """

    def __init__(self):
        """
        The constructor creates the argument parser and parses the arguments.
        """
        self.extlib_tool_name = os.path.splitext(os.path.basename(__file__))[0]
        self.extlib_tool_version = "0.1.0"
        self.__create_parser()

        args = self.parser.parse_args(namespace=argparse.Namespace(extlib_parser=self))
        args.func(args)

    """ Private class methods """

    class __ver_action(argparse.Action):
        def __init__(self, option_strings, dest, **kwargs):
            super().__init__(
                option_strings, dest, nargs=0, default=argparse.SUPPRESS, **kwargs
            )

        def __call__(self, parser, namespace, values, option_string=None):
            # Retrieve the package_parser object from the namespace
            extlib_parser = getattr(namespace, "extlib_parser", None)
            print(
                extlib_parser.extlib_tool_name
                + " version: "
                + extlib_parser.extlib_tool_version
            )
            parser.exit()

    def __main_parser_func(self, args):
        """
        Main parser function of arduino extlib tool
        """
        self.parser.print_help()

    def __mode_parser_func(self, args):
        """
        Version parser function of arduino extlib tool
        """

        if args.extlib_yml is None:
            args.extlib_yml = os.path.join(args.root_path, ".extlib.yml")

        extlib = ExtLib(args.extlib_yml, args.root_path)
        extlib.set_mode(args.submodule, args.mode)

    def __verify_parser_func(self, args):
        """
        Verify parser function of arduino extlib tool
        """
        if args.extlib_yml is None:
           args.extlib_yml = os.path.join(args.root_path, ".extlib.yml")

        extlib = ExtLib(args.extlib_yml, args.root_path)
        extlib.verify(args.submodule)

    def __create_parser(self):
        """
        Creates the argument parser for the extlib tool CLI parser
        """

        def add_shared_args(parser):
            # Argument for library root path
            parser.add_argument(
                "-r",
                "--root-path",
                type=str,
                default=os.getcwd(),
                help="Path to the arduino library root directory. Default is the current directory",
            )

            # Argument for extlib yaml 
            parser.add_argument(
                "-e",
                "--extlib-yml",
                type=str,
                default=None,
                help="Path to the extlib.yml file. Default is <root-path>/extlib.yml",
            )

            # Argument for the submodule library
            parser.add_argument(
                "-s",
                "--submodule",
                type=str,
                default=None,
                help='Name of the external library submodule. Including path (i.e.) "extras/libfoo". If not provided, all submodules will be processed.',
            )

        self.parser = argparse.ArgumentParser(
            description="Arduino library external lib integration utility",
        )

        # Argument for version
        self.parser.add_argument(
            "-v",
            "--version",
            action=self.__ver_action,
            help=self.extlib_tool_name + " version",
        )

        # Set the main parser function
        self.parser.set_defaults(func=self.__main_parser_func)
        add_shared_args(self.parser)

        # Add subparsers
        subparsers = self.parser.add_subparsers()

        # Add the "mode" subparser
        mode_parser = subparsers.add_parser(
            "mode",
            help="Set mode as symlink or copy",
        )
        mode_parser.set_defaults(func=self.__mode_parser_func)
        add_shared_args(mode_parser)

        # Argument for for mode
        mode_parser.add_argument(
            "mode",
            type=str,
            choices=["symlink", "copy"],
            help="Mode to set for the external library submodule.",
        )

        '''
        # TODO: Enable in future ?
        # Argument for the new version
        mode_parser.add_argument(
            "--ref",
            type=str,
            default=None,
            help="Reference or version of the library. Default will be the registered submodule reference.",
        )
        '''

        # Add the "verify" subparser
        verify_parser = subparsers.add_parser(
            "verify",
            help="Verify that the copied lib version match the library submodule version.",
        )
        verify_parser.set_defaults(func=self.__verify_parser_func)
        add_shared_args(verify_parser)

if __name__ == "__main__":

    extlib_parser = ExtlibParser()
