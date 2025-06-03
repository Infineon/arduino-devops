import argparse
import json
import logging
import os
import re
import requests
import sys
import semver
import subprocess
import time

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

class ReleaseLogger:
    """
    Logger class to enable formatted console output.
    """

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
        """
        Prints an info message.
        To be used before performing any operation which 
        will later be completed with the result of the operation ok(), error() or skip().

        Args:
            msg: The message to be printed.
        """
        print(f"{self.blue_on} -->{self.color_off} {msg}", end=" ")
        self.last_msg_ncol = len(msg) + len(" -->  ")

    def step_details(self, msg, highlighted="", end="\n"):
        """
        Prints extended details of the current operation.
        This is just to indent that message below the info_step message.
        Additionally, it can highlight a part of the message.

        Args:
            msg: The message to be printed.
            highlighted: A second msg to be highlighted in the output.
        """
        print(f"     {msg}{self.yellow_on}{highlighted}{self.color_off}", end=end)
    
    def del_line(self, time_s=0):
        """ 
        Deletes the last line printed in the console and moes the cursor back up.
        If a delay is specified, it will wait for that time before deleting the line.

        Args:
            time_s: The time in seconds to wait before deleting the line. Default is 0.
        """
        time.sleep(time_s)
        print("\033[F\033[K", end="")

    def cursor_back_up(self):
        """
        Moves the cursor to the upper line and set the cursor and the end 
        of the line of the last message printed by info_step.
        """
        print(f"\033[F\033[{self.last_msg_ncol}G", end="")
    
    def color_msg(self, msg, color, end="\n"):
        """
        Prints a message in the specified color.

        Args:
            msg: The message to be printed.
            color: The color to be used. It can be one of the following: "blue", "green", "red", "grey", "yellow".
            end: The end character to be used. Default is newline.
        """
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
        """
        Prints a 3 dots animation in the console. Each iteration takes 4 seconds.
        To be used for waiting for some operation to complete, and show the user 
        that the operation is in progress.

        Args:
            iterations: The number of iterations to perform. Each iteration will take 4 seconds.
        """
        for j in range(iterations):
            for i in range(3):
                print(f"{self.yellow_on}.{self.color_off}", end="", flush=True)
                time.sleep(1)
            print("\b\b\b   \b\b\b", end="", flush=True)  
            time.sleep(1)

class Release:
    """
    Class to manage the release of an Arduino asset (library or core).
    """

    def __init__(self, root_path, any_branch=False):
        """
        Constructor of the release class.

        Args:
            root_path: The path to the arduino asset (library or core) root directory.
            any_branch: If True, the release can be created from any branch. Otherwise,
                        the release can only be created from a permanent branch (main or master).
        """
        self.root_path = root_path
        self.any_branch = any_branch
        self.permanent_branches = ["main", "master"]
        self.skip_workflow = "release"
        self.log = ReleaseLogger()

    def new(self, version):
        """
        Creates a new release for the specified version.

        This method performs the following checks:
        - Asserts that the HEAD is in a permanent branch (main or master) unless `any_branch` is set to True.
        - Asserts that all CI workflows are successful for the HEAD commit.
        - Asserts that the HEAD is not already tagged.

        If all checks pass, it performs the following actions:
        - Gets the previous version from the git tags.
        Then:
        - Validates the new version if a numeric semver version is passed 
        or
        - Performs a version bump (major, minor, patch)

        If the asset type is a library:
        - Updates the `library.properties` file with the new version.
        - Commits the changes to the `library.properties` file.

        Then finally:
        - Creates a new git tag with the new version.
        - Pushes the new git tag to the remote repository.

        Args:
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

        if self.__get_asset_type() == "library":
            self.__update_lib_properties(new_version)
            self.__git_commit_change(new_version)
        
        self.__git_tag(new_version)
        self.__git_push_tag(new_version)


    def verify(self):
        """
        Verifies all requirements are met for a new release.
        
        This method performs the following checks:
        - Asserts that all CI workflows are successful for the HEAD commit.
        - Validates that the new version is a valid semver increment compared to the previous version.
        - If the asset type is a library, it asserts that the `library.properties` file has the
          same version as the git tag.
        """
        self.__assert_ci_workflows_success()
        current_tag = self.__get_head_tag()
        previous_tag = self.__get_previous_tag()

        self.__validate_new_numeric(previous_tag, current_tag)
        
        if self.__get_asset_type() == "library":
            self.__assert_lib_properties_version(current_tag)

    def info(self, key):
        """
        Prints the value of the repository information for the specified key.
        The available keys are:
            - "head-tag": The tag of the HEAD commit.
            - "repo-name": The name of the repository (owner/name).
            - "asset-type": The type of the asset (library or core).

        Args:
            key: The key for which the value should be printed. It can be either "head-tag", "repo-name" or "asset-type".
        """
        if key == "head-tag":
            print(self.__get_head_tag(log=False))
        elif key == "repo-name":
            print(self.__get_repo_owner_name()[1])
        elif key == "asset-type":
            print(self.__get_asset_type())
        else:
            print("Key not recognized. Available keys are: 'head-tag', 'repo-name', 'asset-type'.")
            sys.exit(1)

    """ Private methods """

    def __validate_new_numeric(self, previous_version, version_bump):
        """
        Checks if the new version is a valid semver version and if it is a valid increment
        compared to the previous version.
        Args:
            previous_version: The previous version to compare with.
            version_bump: The new version to validate. It can be either a version number (semver x.y.z) or a version bump (major, minor, patch).

        Returns:
            The new version as a semver.VersionInfo object if it is a valid increment.
            Otherwise, it exits the program with an error message.
        """

        def is_valid_increase(new_version, previous_version):
            """
            Check if the new version is a valid semver increment compared to the previous version.
            A valid increment fulfills the following conditions:
            - If the major version is increased, the minor and patch versions should be 0.
            - If the minor version is increased, the patch version should be 0.
            - If the patch version is increased, the minor version should be the same.
            - Any of the numbers can be only increased by 1.

            Args:
                new_version: The new version to validate.
                previous_version: The previous version to compare with.
            Returns:
                True if the new version is a valid semver increment.
                False otherwise.
            """
            if new_version.major > previous_version.major:
                return new_version.major == previous_version.major + 1 and new_version.minor == 0 and new_version.patch == 0
            elif new_version.minor > previous_version.minor:
                return new_version.minor == previous_version.minor + 1 and new_version.patch == 0 and new_version.major == previous_version.major
            elif new_version.patch > previous_version.patch:
                return new_version.patch == previous_version.patch + 1 and new_version.minor == previous_version.minor and new_version.major == previous_version.major
            return False
        
        def is_valid_from_release_candidate(new_version, previous_version):
            """
            Check if the new version is a valid semver increment from a release candidate.
            A valid increment from a release candidate fulfills the following conditions:
            - If the previous version is a prerelease (release candidate), the new version can be a normal release.
            - The major, minor and patch versions should be the same as the previous version.
            - The prerelease version should be different from the previous version.

            Args:
                new_version: The new version to validate.
                previous_version: The previous version to compare with.
            Returns:
                True if the new version is a valid semver increment from a release candidate.
                False otherwise.
            """
            if previous_version.prerelease and \
                new_version.major == previous_version.major and \
                new_version.minor == previous_version.minor and \
                new_version.patch == previous_version.patch and \
                new_version.prerelease != previous_version.prerelease:
                return True
            return False

        # Allow for vV prefix in the version. 
        # This is added to support legacy tags versioning used in some Arduino libraries.
        previous_version = self.__strip_prefix_from_version(previous_version)

        try:
            new_version = semver.VersionInfo.parse(version_bump)
            previous_version = semver.VersionInfo.parse(previous_version)
        except ValueError:
            self.log.error()
            self.log.step_details("The chosen version is not a valid semver format: ", version_bump)
            sys.exit(1)
        
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
        """
        Bumps the previous version according to the specified version bump type (major, minor, patch).

        Args:
            previous_version: The previous version to bump.
            version_bump: The type of version bump to perform. It can be either "major", "minor" or "patch".
        Returns:
            The new version as a semver.VersionInfo object.
        """
        self.log.info_step("New bumped version :")

        # Allow for vV prefix in the version. 
        # This is added to support legacy tags versioning used in some Arduino libraries.
        previous_version = self.__strip_prefix_from_version(previous_version)

        new_version = semver.VersionInfo.parse(previous_version)
        if version_bump == "major":
            new_version = new_version.bump_major()
        elif version_bump == "minor":
            new_version = new_version.bump_minor()
        elif version_bump == "patch":
            new_version = new_version.bump_patch()

        self.log.color_msg(new_version, "blue")

        return new_version

    def __strip_prefix_from_version(self, version):
        """
        Strips 'v' or 'V' prefix from version.

        Args:
            version: The version string to be stripped.
        Returns:
            The version string without the 'v' or 'V' prefix.
        """
        return re.sub(r"[vV]", "", version)

    def __assert_permanent_branch(self):
        """
        Asserts if the repo HEAD is in a permanent branch (main or master).
        If the HEAD is not in a permanent branch, it exits the program with an error message.

        If the `any_branch` flag is set to True, it skips this check
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
        Asserts if all the Github Actions workflows are successful for the HEAD commit.
        If any workflow fails, it exits the program with an error message.

        The method performs the following steps:
        - Retrieves the workflows for the HEAD commit using the GitHub API.
        - Wait for all workflows to complete if they are still in progress.
        - Asserts that all workflows are successful.
        """

        def get_workflow_runs(repo_owner, repo_name, branch, commit_hash):
            """
            Retrieves the GitHub Action workflow runs for the specified repository, branch and commit.

            Args:
                - repo_owner: The owner of the repository.
                - repo_name: The name of the repository.
                - branch: The branch to check the workflows for.
                - commit_hash: The commit hash to check the workflows for.
            Returns:
                A list of workflow runs for the specified repository, branch and commit.
            """
            request = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/runs?branch={branch}&head_sha={commit_hash}" 
            response = requests.get(request)
            if response.status_code != 200:
                self.log.error()
                self.log.step_details("Error retrieving workflows for commit ", commit_hash)
                self.log.step_details("Response code: ", response.status_code)
                sys.exit(1)
            
            return response.json().get("workflow_runs", [])

        def assert_workflow_runs_status(workflows):
            """
            Asserts that all workflows are successful.
            If any workflow fails, it exits the program with an error message.

            The key "conclusion" in the workflow run indicates the final status of the workflow.
            The workflow is skipped if the workflow name contains "release" (case insensitive),
            as this would be the current workflow being executed.

            Args:
                - workflows: A list of workflow runs to check the status for.
            """
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

            The key "status" in the workflow run indicates the current status of the workflow.
            The workflow is considered in progress if the status is "in_progress" or "requested".

            The workflow is skipped if the workflow name contains "release" (case insensitive),
            as this would be the current workflow being executed.

            Args:
                - workflows: A list of workflow runs to check the status for.

            Returns:
                True if all workflows are completed, False otherwise.
                If any workflow is in progress, it prints the name of the workflow and returns False.
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
        """
        Gets the current branch of the HEAD commit.
        Returns:
            The name of the current branch.
        """
        return os.popen(f"git -C {self.root_path} rev-parse --abbrev-ref HEAD").read().strip()

    def __get_repo_owner_name(self):
        """
        Gets the owner and name of the repository from the remote URL.

        It uses the `git config --get remote.origin.url` command to retrieve the remote URL.   
        The remote URL can be either in HTTPS or SSH format.

        Returns:
            A tuple containing the owner and name of the repository.
            If the remote URL is not recognized, it exits the program with an error message.
        """
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
        Asserts that the HEAD commit is not already tagged.
        If the HEAD commit is already tagged, it exits the program with an error message.
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
        Gets the lastest version from the git tags.

        Returns:
            The last version as a string. If no tags are found, it returns "0.0.0".
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
        Gets the tag of the HEAD commit.
        If the HEAD commit is not tagged, it exits the program with an error message.

        Args:
            log: If True, it logs the information. Default is True.
        Returns:
            The tag of the HEAD commit as a string.
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
        Gets the previous tag from the git tags.
        If no previous tag is found, it returns "0.0.0" and logs a message.

        Returns:
            The previous tag as a string. If no previous tag is found, it returns "0.0.0".
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

    def __update_lib_properties(self, new_version):
        """
        Updates the `library.properties` file with the new version.

        Args:
            new_version: The new version to be set in the `library.properties` file.
        """
        self.log.info_step("Updating \"library.properties\" file with new version...")

        properties_file = os.path.join(self.root_path, "library.properties")
        with open(properties_file, "r") as f:
            lines = f.readlines()

        with open(properties_file, "w") as f:
            for line in lines:
                if line.startswith("version="):
                    f.write(f"version={new_version}\n")
                else:
                    f.write(line)
        self.log.ok()
        

    def __git_commit_change(self, new_version):
        """
        Commits the changes to the `library.properties` file with the new version.

        It checks if the git user is set, and if not, it sets the git user to a default value.
        The default git user is set to 'github-actions[bot]' with a noreply email.

        Args:
            new_version: The new version to be set in the commit message.
        """
        def is_git_user_set():
            """
            Checks if the git user is set.
            """
            param = "user.name"
            git_cmd = ["git", "-C", self.root_path, "config", "--get", param]
            git_proc_name = subprocess.run(git_cmd, capture_output=True, text=True, check=False)

            param = "user.email"
            git_proc_email = subprocess.run(git_cmd, capture_output=True, text=True, check=False)   
            
            return git_proc_name.stdout.strip() != "" and git_proc_email.stdout.strip() != "" 

        def set_git_user(user, email):
            """
            Sets the git user and email to the specified values.

            Args:
                user: The git user name to be set.
                email: The git user email to be set.
            """
            self.log.info_step("Setting git user and email...")
            command = ["git", "-C", self.root_path, "config", "--local", "user.name", user]
            git_proc_user = subprocess.run(command, capture_output=True, text=True, check=False)
            
            if git_proc_user.returncode != 0:
                self.log.error()
                self.log.step_details("Error setting git user: ", git_proc_user.stderr.strip())
                sys.exit(1)

            command = ["git", "-C", self.root_path, "config", "--local", "user.email", email]
            git_proc_email = subprocess.run(command, capture_output=True, text=True, check=False)
            
            if git_proc_email.returncode != 0:
                self.log.error()
                self.log.step_details("Error setting git email: ", git_proc_email.stderr.strip())
                sys.exit(1)

            self.log.ok()

        
        if not is_git_user_set():
            set_git_user('github-actions[bot]', 'github-actions[bot]@users.noreply.github.com')
        
        self.log.info_step("Committing changes to library.properties file...")
        command = ["git", "-C", self.root_path, "add", "library.properties"]
        git_proc_add = subprocess.run(command, capture_output=True, text=True, check=False)
        if git_proc_add.returncode != 0:
            self.log.error()
            self.log.step_details("Error adding library.properties file: ", git_proc_add.stderr.strip())
            sys.exit(1)
        
        command = ["git", "-C", self.root_path, "commit", "-s", "-m", f"library.properties: Bumped version to {new_version}."]
        git_proc_commit = subprocess.run(command, capture_output=True, text=True, check=False)
        if git_proc_commit.returncode != 0:
            self.log.error()
            self.log.step_details("Error committing library.properties file: ", git_proc_commit.stderr.strip())
            sys.exit(1)
        
        self.log.ok()

    def __git_tag(self, new_version):
        """
        Creates a new git tag with the new version.

        Args:
            new_version: The new version to be set as a git tag.
        """
        self.log.info_step("Creating new git tag...")
        command = ["git", "-C", self.root_path, "tag", str(new_version)]
        git_proc = subprocess.run(command, capture_output=True, text=True, check=False)
        
        if git_proc.returncode != 0:
            self.log.error()
            self.log.step_details("Error creating git tag: ", git_proc.stderr.strip())
            sys.exit(1)
        
        self.log.ok()

    def __git_push_tag(self, new_version):
        """
        Pushes the new git tag to the remote repository.

        Args:
            new_version: The new version to be pushed as a git tag.
        """
        self.log.info_step("Pushing new git tag...")
        branch = self.__get_head_branch()
        command = ["git", "push", "origin", branch, str(new_version)]
        git_proc = subprocess.run(command, capture_output=True, text=True, check=False)
        
        if git_proc.returncode != 0:
            self.log.error()
            self.log.step_details("Error pushing git tag: ", git_proc.stderr.strip())
            sys.exit(1)
        
        self.log.ok()

    def __assert_lib_properties_version(self, current_tag):
        """
        Asserts that the library.properties file has the correct version.

        Args:
            current_tag: The current tag of the HEAD commit. This should match the version in the library.properties file.
        """
        self.log.info_step("Validating \"library.properties\" version field...")
        properties_file = os.path.join(self.root_path, "library.properties")
        with open(properties_file, "r") as f:
            lines = f.readlines()

        for line in lines:
            if line.startswith("version="):
                version = line.split("=")[1].strip()
                if version != current_tag:
                    self.log.error()
                    self.log.step_details("New version does not match \"library.properties\" version field : ", version)
                    sys.exit(1)
                else:
                    self.log.ok()
                return
        
        self.log.error()
        self.log.step_details("\"library.properties\" file does not contain a version field.")
        sys.exit(1)

    def __get_asset_type(self):
        """
        Gets the asset type based on the root path content.
        The asset type can be either a library or a core.
            - A library is considered when the "library.properties" file is present in the asset root path.
            - A core is considered when the "platform.txt" and "board.txt" files and
            the "cores" and "variants" directories are present in the asset root path.
        
        Returns:
            The asset type as a string. It can be either "library" or "core".
        """
        if os.path.exists(os.path.join(self.root_path, "library.properties")):
            return "library"
        elif os.path.exists(os.path.join(self.root_path, "platform.txt")) and \
             os.path.exists(os.path.join(self.root_path, "boards.txt")) and \
             os.path.exists(os.path.join(self.root_path, "variants")) and \
             os.path.exists(os.path.join(self.root_path, "cores")):
            return "core"
        else:
            logging.error(f"Asset type not found. The asset root path \"{self.root_path}\" does not contain a valid library or core.")
            sys.exit(1) 


class ReleaseParser:
    """
    Class that parses the release tool arguments
    """

    def __init__(self):
        """
        The constructor creates the argument parser and parses the arguments.
        """
        self.release_tool_name = os.path.splitext(os.path.basename(__file__))[0]
        self.release_tool_version = "0.2.0"
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
        self.parser.print_help()

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