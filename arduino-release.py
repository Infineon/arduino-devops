import argparse
import json
import logging
import os
import requests
import sys
import semver
import subprocess
import time

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

class ReleaseLogger:

    def __init__(self):
        self.blue_on = "\033[94m"
        self.green_on = "\033[92m"
        self.red_on = "\033[91m"
        self.grey_on = "\033[90m"
        self.yellow_on = "\033[95m"
        self.color_off = "\033[0m"

    def ok(self):
        print(f"{self.green_on} [OK] {self.color_off}")
    
    def error(self):
        print(f"{self.red_on} [ERROR] {self.color_off}")
    
    def skip(self):
        print(f"{self.grey_on} [SKIP] {self.color_off}")

    def info_step(self, msg):
        print(f"{self.blue_on} -->{self.color_off} {msg}", end=" ")
        self.last_msg_ncol = len(msg) + len(" -->  ")

    def step_details(self, msg, highlighted="", end="\n"):
        print(f"     {msg}{self.yellow_on}{highlighted}{self.color_off}", end=end)
    
    def del_line(self, time_s=0):
        time.sleep(time_s)
        print("\033[F\033[K", end="")

    def cursor_back_up(self):
        # Move cursor up n lines
        print(f"\033[F\033[{self.last_msg_ncol}G", end="")
    
    def color_msg(self, msg, color, end="\n"):
        if color == "blue":
            print(f"{self.blue_on}{msg}{self.color_off}", end=end)
        elif color == "green":
            print(f"{self.green_on}{msg}{self.color_off}", end=end)
        elif color == "red":
            print(f"{self.red_on}{msg}{self.color_off}", end=end)
        elif color == "grey":
            print(f"{self.grey_on}{msg}{self.color_off}", end=end)
        elif color == "yellow":
            print(f"{self.yellow_on}{msg}{self.color_off}", end=end)
        else:
            print(msg, end=end)

    def wait_progress_animation(self, iterations):
        # Every iteration will take 4 seconds
        for j in range(iterations):
            for i in range(3):
                print(f"{self.yellow_on}.{self.color_off}", end="", flush=True)
                time.sleep(1)
            print("\b\b\b   \b\b\b", end="", flush=True)  
            time.sleep(1)

class Release:

    def __init__(self, root_path, any_branch=False):
        """
        The constructor creates the argument parser and parses the arguments.
        """
        self.root_path = root_path
        self.any_branch = any_branch
        self.permanent_branches = ["main", "master"]
        self.skip_workflow = "release"
        self.log = ReleaseLogger()

    def new(self, version):
        """
        Create a new release if all the conditions are met.

        args:
            version: The new version to be set. It can be either a version number (semver x.y.z) or a version bump (major, minor, patch).
        """

        self.__assert_permanent_branch()
        self.__assert_ci_workflows_success()
        self.__assert_head_not_tagged()

        current_version = self.__get_latest_version()    
        
        if version in ["major", "minor", "patch"]: 
            new_version = self.__new_bump(current_version, version)
        else:
            new_version = self.__validate_new_numeric(current_version, version)

        if self.__is_asset_library():
            self.log.info_step("Updating library.properties file with new version: ")
            self.__update_lib_properties(new_version)
            self.__git_commit_change(new_version, user, email)
        
        # check here if all works with pre-commit hooks, if we should do the push manually.
        self.__git_tag(new_version)
        self.__git_push_tag(new_version)


    def verify(self):
        # all workflows are green for this commit/branch
        self.__assert_ci_workflows_success()
        current_tag = self.__get_head_tag()
        previous_tag = self.__get_previous_tag()

        self.__validate_new_numeric(previous_tag, current_tag)
        
        if self.__is_asset_library():
            pass # TODO: Next iteration. Current focus on core.
            self.log.info_step("Checking library.properties file with new version: ")

    def info(self, key):
        if key == "head-tag":
            print(self.__get_head_tag(log=False))
        elif key == "repo-name":
            print(self.__get_repo_owner_name()[1])
        elif key == "asset-type":
            # TODO: Implement a proper check for asset type
            print("library" if self.__is_asset_library() else "core")
        else:
            print("Key not recognized. Available keys are: 'head-tag', 'repo-name', 'asset-type'.")
            sys.exit(1)

    def __validate_new_numeric(self, previous_version, version_bump):
        # Check if the version is a valid semver version
        # Check if it is valid increase compared to the previous version
        try:
            new_version = semver.VersionInfo.parse(version_bump)
            previous_version = semver.VersionInfo.parse(previous_version)
        except ValueError:
            self.log.error()
            self.log.step_details("The chosen version is not a valid semver format: ", version_bump)
            sys.exit(1)
        
        def is_valid_increase(new_version, previous_version):
            #The new version should be greater than the previous version and a valid
            if new_version.major > previous_version.major:
                return new_version.major == previous_version.major + 1 and new_version.minor == 0 and new_version.patch == 0
            elif new_version.minor > previous_version.minor:
                return new_version.minor == previous_version.minor + 1 and new_version.patch == 0 and new_version.major == previous_version.major
            elif new_version.patch > previous_version.patch:
                return new_version.patch == previous_version.patch + 1 and new_version.minor == previous_version.minor and new_version.major == previous_version.major
            return False
        
        def is_valid_from_release_candidate(new_version, previous_version):
            # The new version should be greater than the previous version and a valid
            if previous_version.prerelease and \
                new_version.major == previous_version.major and \
                new_version.minor == previous_version.minor and \
                new_version.patch == previous_version.patch and \
                new_version.prerelease != previous_version.prerelease:
                return True
            return False

        self.log.info_step("Validating new version")
        self.log.color_msg(new_version, "yellow", end="") 
        self.log.color_msg(" ...", "none", end="") 

        if not is_valid_increase(new_version, previous_version) and \
           not is_valid_from_release_candidate(new_version, previous_version):
            self.log.error()
            self.log.step_details("The new version is not a valid semver increment.")
            sys.exit(1)

        self.log.ok()
        return new_version

    def __new_bump(self, previous_version, version_bump):
        
        self.log.info_step("New bumped version :")

        new_version = semver.VersionInfo.parse(previous_version)
        if version_bump == "major":
            new_version = new_version.bump_major()
        elif version_bump == "minor":
            new_version = new_version.bump_minor()
        elif version_bump == "patch":
            new_version = new_version.bump_patch()

        self.log.color_msg(new_version, "blue")

        return new_version

    def __assert_permanent_branch(self):
        """
        Check if the repo HEAD is in a permanent branch (main or master).
        """
        
        self.log.info_step("Checking if repo HEAD in the default branch...")

        if self.any_branch:
            self.log.skip()
            return

        branch = self.__get_head_branch()
        if branch not in self.permanent_branches:
            self.log.error()
            self.log.step_details("Release is allowed only from permanent branches: ", self.permanent_branches)
            self.log.step_details("HEAD is in branch: ", branch)
            sys.exit(1)
        else:
            self.log.ok()

    
    def __assert_ci_workflows_success(self):
        """
        Check if all the workflows are green for the latest commit in the main branch.
        """

        def get_workflow_runs(repo_owner, repo_name, branch, commit_hash):
            request = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/runs?branch={branch}&head_sha={commit_hash}" 
            response = requests.get(request)
            if response.status_code != 200:
                self.log.error()
                self.log.step_details("Error retrieving workflows for commit ", commit_hash)
                self.log.step_details("Response code: ", response.status_code)
                sys.exit(1)
            
            return response.json().get("workflow_runs", [])

        def assert_workflow_runs_status(workflows):
            print()
            for wflow in workflows:
                self.log.step_details(wflow["name"], end=" ")
                if wflow["conclusion"] == "failure":
                    if self.skip_workflow in wflow["name"].lower():
                        continue
                    self.log.error()
                    sys.exit(1)
                self.log.ok()
                # Remove back all the lines written here in the console
                delay_s = 0.5
                self.log.del_line(delay_s)
            
            # Move cursor up to the end of the previous line 
            self.log.cursor_back_up()

        def assert_workflows_completion(workflows):
            """
            Assert that all workflows are completed.
            """
            for wflow in workflows:
                if wflow["status"] == "in_progress" or wflow["status"] == "requested":
                    # Skip workflows that are related to the release
                    if self.skip_workflow in wflow["name"].lower():
                        continue
                    print()
                    self.log.step_details(f"Workflow in progress : ", wflow["name"],  end=" ")
                    self.log.cursor_back_up()
                    return False
                
            return True


        branch = self.__get_head_branch()
        commit_hash = os.popen(f"git -C {self.root_path} rev-parse HEAD").read().strip()
        repo_owner, repo_name = self.__get_repo_owner_name()

        self.log.info_step("Waiting for all ci workflows completion for HEAD")

        workflows = get_workflow_runs(repo_owner, repo_name, branch, commit_hash)
        while not assert_workflows_completion(workflows):
            iter_for_16_s = 4 # Each iteration will take 4 seconds
            self.log.wait_progress_animation(iter_for_16_s)
            workflows = get_workflow_runs(repo_owner, repo_name, branch, commit_hash)

        self.log.color_msg("...", None , end="")
        self.log.ok()
            
        self.log.info_step("Checking if all ci workflows are successful for HEAD...")

        workflows = get_workflow_runs(repo_owner, repo_name, branch, commit_hash)
        assert_workflow_runs_status(workflows)

        self.log.ok()


    def __get_head_branch(self):
        return os.popen(f"git -C {self.root_path} rev-parse --abbrev-ref HEAD").read().strip()

    def __get_repo_owner_name(self):
        remote = os.popen(f"git -C {self.root_path} config --get remote.origin.url").read().strip()
        gh_https_url = "https://github.com/"
        gh_ssh_url = "git@github.com:"

        if gh_https_url in remote:
            # The owner is the fourth substring of the URL splitted by "/"
            owner = remote.split("/")[3]
            # The name is the fifth substring of the URL splitted by "/"
            if remote.endswith(".git"):
                name = remote.split("/")[4][:-4]
            else:
                name = remote.split("/")[4]
            return owner, name
        elif gh_ssh_url in remote:
            # The owner is just the first part of the URL after the semicolon
            owner = remote.split(":")[1].split("/")[0]
            # The owner is the second part of the URL after the semicolon
            if remote.endswith(".git"):
                name = remote.split(":")[1].split("/")[1][:-4]
            else:
                name = remote.split(":")[1].split("/")[1][:-4]
            return owner, name
        else:
            self.log.error()
            self.log.step_details("Remote URL is not recognized. Only GitHub remote is supported.")
            sys.exit(1)

    def __assert_head_not_tagged(self):
        """
        Check if the HEAD is tagged.
        """
        self.log.info_step("Checking if HEAD is not already tagged...")

        command = ["git", "-C", self.root_path, "describe", "--tags", "--exact-match"]
        git_proc = subprocess.run(command, capture_output=True, text=True, check=False)
        
        if git_proc.returncode == 0:
            self.log.error()
            self.log.step_details("This HEAD is already tagged as : ", git_proc.stdout.strip())
            sys.exit(1)
        else:
            self.log.ok()

    def __get_latest_version(self):
        """
        Get the last version from the git tags.
        """
        self.log.info_step("Previous last version :")
        command = ["git", "-C", self.root_path, "describe", "--tags", "--abbrev=0"]
        git_proc = subprocess.run(command, capture_output=True, text=True, check=False)

        if git_proc.returncode != 0:
            self.log.color_msg("0.0.0", "yellow")
            self.log.step_details("No tag found. Set the initial version as ", "0.0.0")
            return "0.0.0"

        last_version = git_proc.stdout.strip()
        self.log.color_msg(last_version, "blue")

        return last_version

    def __get_head_tag(self, log=True):
        """
        Get the tag of the HEAD commit.
        """
        if log:
            self.log.info_step("HEAD tag :")

        command = ["git", "-C", self.root_path, "describe", "--tags", "--exact-match"]
        git_proc = subprocess.run(command, capture_output=True, text=True, check=False)
        
        if git_proc.returncode != 0:
            if log:
                self.log.error()
            self.log.step_details("HEAD is not tagged. ", git_proc.stderr.strip())
            sys.exit(1)
        
        head_tag = git_proc.stdout.strip()
        if log:
            self.log.color_msg(head_tag, "blue")

        return head_tag

    def __get_previous_tag(self):
        """
        Get the previous tag from the git tags.
        """
        self.log.info_step("Previous tag :")
        command = ["git", "-C", self.root_path, "describe", "--tags", "--abbrev=0", "HEAD^"]
        git_proc = subprocess.run(command, capture_output=True, text=True, check=False)
        
        if git_proc.returncode != 0:
            self.log.color_msg("0.0.0", "yellow")
            self.log.step_details("No tag found. Set the initial version as ", "0.0.0")
            return "0.0.0"
        
        previous_tag = git_proc.stdout.strip()
        self.log.color_msg(previous_tag, "blue")

        return previous_tag

    def __is_asset_library(self):
        """
        Checks if the asset is an Arduino library. 
        If that is the case, it should contain a library.properties file.
        """
        if os.path.exists(os.path.join(self.root_path, "library.properties")):
            return True

        return False

    def __update_lib_properties(self, new_version):
        pass
        # TODO: Next iteration. Current focus on core.

    def __git_commit_change(self, new_version, user, email):
        pass
        # TODO: Next iteration. Current focus on core.
    
    def __git_tag(self, new_version):
        """
        Create a new git tag with the new version.
        """
        self.log.info_step("Creating new git tag... ")
        command = ["git", "-C", self.root_path, "tag", str(new_version)]
        git_proc = subprocess.run(command, capture_output=True, text=True, check=False)
        
        if git_proc.returncode != 0:
            self.log.error()
            self.log.step_details("Error creating git tag: ", git_proc.stderr.strip())
            sys.exit(1)
        
        self.log.ok()

    def __git_push_tag(self, new_version):
        """
        Push the new git tag to the remote repository.
        """
        self.log.info_step("Pushing new git tag... ")
        command = ["git", "push", "origin", str(new_version)]
        git_proc = subprocess.run(command, capture_output=True, text=True, check=False)
        
        if git_proc.returncode != 0:
            self.log.error()
            self.log.step_details("Error pushing git tag: ", git_proc.stderr.strip())
            sys.exit(1)
        
        self.log.ok()

class ReleaseParser:

    def __init__(self):
        """
        The constructor creates the argument parser and parses the arguments.
        """
        self.release_tool_name = os.path.splitext(os.path.basename(__file__))[0]
        self.release_tool_version = "0.1.0"
        self.__create_parser()

        args = self.parser.parse_args(namespace=argparse.Namespace(release_parser=self))
        args.func(args)

    """ Private class methods """

    class __ver_action(argparse.Action):
        def __init__(self, option_strings, dest, **kwargs):
            super().__init__(
                option_strings, dest, nargs=0, default=argparse.SUPPRESS, **kwargs
            )

        def __call__(self, parser, namespace, values, option_string=None):
            # Retrieve the package_parser object from the namespace
            release_parser = getattr(namespace, "release_parser", None)
            print(
                release_parser.release_tool_name
                + " version: "
                + release_parser.release_tool_version
            )
            parser.exit()

    def __main_parser_func(self, args):
        """
        Main parser function of arduino release tool.
        """
        print("main parser function")

    def __new_version_parser_func(self, args):
        """
        Version parser function of arduino release tool.
        """
        release = Release(args.root_path, args.any_branch)
        release.new(args.version)
    
    def __verify_parser_func(self, args):
        """
        Verify version parser function of arduino release tool.
        """
        release = Release(args.root_path)
        release.verify()

    def __info_parser_func(self, args):
        """
        Info version parser function of arduino release tool.
        """
        release = Release(args.root_path)
        release.info(args.key)
    
    def __create_parser(self):
        """
        Creates the argument parser for the release tool CLI parser.
        """

        def add_shared_args(parser):
            # Argument for asset (core or library) root path
            parser.add_argument(
                "-r",
                "--root-path",
                type=str,
                default=os.getcwd(),
                help="Path to the arduino asset (library or core) root directory. Default is the current directory",
            )

        self.parser = argparse.ArgumentParser(
            description="Arduino asset release utility",
        )

        # Argument for version
        self.parser.add_argument(
            "-v",
            "--version",
            action=self.__ver_action,
            help=self.release_tool_name + " version",
        )

        # Set the main parser function
        self.parser.set_defaults(func=self.__main_parser_func)
        add_shared_args(self.parser)    

        # Add subparsers 
        subparsers = self.parser.add_subparsers()

        # Add the "new" subparser
        new_parser = subparsers.add_parser(
            "new",
            help="Create a new release",
        )
        new_parser.set_defaults(func=self.__new_version_parser_func)  
        add_shared_args(new_parser)

        # Argument for the new version
        new_parser.add_argument(
            "version",
            type=str,
            default=None,
            help="New version to be set. It can be either a version number (semver x.y.z) or a version bump (major, minor, patch)",
        )

        # Argument for any branch
        new_parser.add_argument(
            "--any-branch",
            action="store_true",
            default=False,
            help="Bypass release requirement: HEAD from permanent branch (main or master)"
        )

        # Add the "verify" subparser
        verify_parser = subparsers.add_parser(
            "verify",
            help="Verify all requirements are met for a new release",
        )
        verify_parser.set_defaults(func=self.__verify_parser_func)
        add_shared_args(verify_parser)

        # Add the "info" subparser
        info_parser = subparsers.add_parser(
            "info",
            help="Release information",
        )
        info_parser.set_defaults(func=self.__info_parser_func)
        add_shared_args(info_parser)

        # Argument for info value
        info_parser.add_argument(
            "key",
            type=str,
            default=None,
            help="Info key to be printed. It can be either 'head-tag', 'repo-name' or 'asset-type'.",
        )


if __name__ == "__main__":

    release_parser = ReleaseParser()