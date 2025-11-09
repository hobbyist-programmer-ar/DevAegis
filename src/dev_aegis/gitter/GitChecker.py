import os
import subprocess
import sys


class GitChecker:
    """
    Handles all Git-related operations, including checking the branch,
    staging files, committing, checking for remote changes, and pushing.
    """
    def __init__(self):
        jira_ticket = input("Please enter the JIRA Ticket ID: ")
        if not jira_ticket:
            print("ERROR: A JIRA Ticket ID is required.")
            sys.exit(1)
        self.project_root = os.getcwd()
        self.jira_ticket = jira_ticket
        self.report_dir = os.path.join(self.project_root, ".dev-aegis")
        self.report_file = os.path.join(self.report_dir, "git-warning-report.md")
        self._ensure_report_directory_exists()
        self.current_branch = self._run_git_command(['rev-parse', '--abbrev-ref', 'HEAD']).strip()
        if not self.current_branch:
            print("ERROR: Could not determine the current Git branch. Are you in a Git repository?")
            sys.exit(1)

    def _ensure_report_directory_exists(self):
        """
        Creates the report directory if it doesn't already exist.
        """
        try:
            os.makedirs(self.report_dir, exist_ok=True)
        except OSError as e:
            print(f"ERROR: Failed to create directory {self.report_dir}: {e}")
            sys.exit(1)

    def _run_git_command(self, command, check=True):
        """Helper to run a Git command and return its output."""
        try:
            result = subprocess.run(['git'] + command, capture_output=True, text=True, cwd=self.project_root, check=check, encoding='utf-8')
            return result.stdout
        except FileNotFoundError:
            print("ERROR: 'git' command not found. Please ensure Git is installed and in your PATH.")
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Git command failed: {' '.join(command)}")
            print(f"STDERR:\n{e.stderr}")
            sys.exit(1)

    def check_current_branch(self):
        """Warns the user if they are on a protected branch."""
        protected_branches = ['main', 'master', 'dev', 'develop']
        print(f"INFO: Currently on branch: '{self.current_branch}'")
        if self.current_branch in protected_branches:
            print(f"WARNING: You are on a protected branch ('{self.current_branch}').")
            response = input("Are you sure you want to continue? (y/n): ").lower()
            if response != 'y':
                print("Aborting operation.")
                return False
        return True

    def stage_files(self):
        """Interactively stages changed and untracked files."""
        status_output = self._run_git_command(['status', '--porcelain'])
        if not status_output:
            print("INFO: No changes to stage.")
            return

        # Parse the output of 'git status --porcelain' to get a list of file paths.
        # This is more robust than slicing with a fixed index, which was causing trimming issues.
        parsed_files = []
        for line in status_output.strip().splitlines():
            # The format is 'XY path'. We lstrip() to handle potential extra leading
            # whitespace and split once to separate the status from the path.
            parts = line.lstrip().split(' ', 1)
            if len(parts) == 2:
                file_path = parts[1]
                # Handle renamed files ('old -> new') by taking the new path.
                if ' -> ' in file_path:
                    parsed_files.append(file_path.split(' -> ')[1])
                else:
                    parsed_files.append(file_path)

        if not parsed_files:
            print("INFO: No changes to stage.")
            return

        add_all = False
        for file_path in parsed_files:
            if add_all:
                self._run_git_command(['add', file_path])
                print(f"Staged: {file_path}")
                continue

            response = input(f"Stage '{file_path}'? (y/n/a/q): ").lower()
            if response == 'y':
                self._run_git_command(['add', file_path])
            elif response == 'a':
                add_all = True
                self._run_git_command(['add', file_path])
                print(f"Staged: {file_path}")
            elif response == 'q':
                print("INFO: Quitting staging process.")
                break
            # 'n' is implicit: do nothing

    def create_commit(self):
        """Creates a commit if there are staged changes."""
        has_staged_changes = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=self.project_root).returncode != 0

        if not has_staged_changes:
            print("INFO: No changes staged for commit. Skipping commit.")
            return

        commit_message = input("Enter your commit message: ")
        full_commit_message = f"{self.jira_ticket}: {commit_message}"
        self._run_git_command(['commit', '-m', full_commit_message])
        print("INFO: Commit created successfully.")

    def check_remote_changes(self):
        """Checks for new commits on main remote branches and creates a report."""
        print("INFO: Fetching from origin to check for remote changes...")
        self._run_git_command(['fetch', 'origin'])

        branches_to_check = ['main', 'master', 'develop', 'dev']
        report_content = ""

        remotes = self._run_git_command(['branch', '-r'])
        for branch in branches_to_check:
            if f'origin/{branch}' in remotes:
                try:
                    log_output = self._run_git_command(['log', f'HEAD..origin/{branch}', '--oneline'], check=False)
                    if log_output.strip():
                        report_content += f"## New Commits on 'origin/{branch}'\n\n"
                        report_content += "```\n" + log_output.strip() + "\n```\n\n"
                except subprocess.CalledProcessError:
                    print(f"WARN: Could not check branch 'origin/{branch}'.")
                    continue

        if report_content:
            final_report = "# Git Remote Changes Warning\n\n" + report_content
            with open(self.report_file, 'w', encoding='utf-8') as f:
                f.write(final_report)
            print(f"WARNING: New commits found on remote branches. Report generated at '{self.report_file}'")
        else:
            print("INFO: No new commits found on main remote branches.")

    def push_to_remote(self):
        """Pushes the current branch to the remote repository."""
        print(f"INFO: Pushing branch '{self.current_branch}' to origin...")
        self._run_git_command(['push', '-u', 'origin', self.current_branch])
        print("INFO: Push successful.")

    def run_full_process(self):
        """Orchestrates all Git-related checks and actions sequentially."""
        if not self.check_current_branch():
            return
        self.stage_files()
        self.create_commit()
        self.check_remote_changes()
        self.push_to_remote()

def main():
    """
    The main function to run the interactive tool.
    """
    project_root = os.getcwd()
    print("--- Developer Assistant ---")
    print(f"--- Running in directory: {project_root} ---")

    git_checker = GitChecker()
    git_checker.run_full_process()

    print("\nINFO: Developer Assistant process completed.")


if __name__ == "__main__":
    main()
