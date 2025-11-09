import os
import subprocess
import sys


class MavenBuilder:
    """
    Handles the Maven build process for a Java project, including logging.
    """
    def __init__(self):
        """
        Initializes the MavenBuilder, setting up the log directory and file paths.
        """
        self.log_dir = ".dev-aegis/build"
        self.log_file = os.path.join(self.log_dir, "build.log")
        self._ensure_log_directory_exists()

    def _ensure_log_directory_exists(self):
        """
        Creates the log directory if it doesn't already exist.
        """
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            print(f"INFO: Log directory '{self.log_dir}' is ready.")
        except OSError as e:
            print(f"ERROR: Failed to create directory {self.log_dir}: {e}")
            sys.exit(1)  # Exit if we can't create the log directory.

    def build(self):
        """
        Runs the 'mvn clean install' command, captures its output, and logs it.

        If the Maven build fails (i.e., exits with a non-zero status code),
        the script will terminate.
        """
        print("INFO: Starting Maven build process...")

        command = ['mvn', 'clean', 'install']
        execution_path = os.getcwd()
        print(f"INFO: Executing command: '{' '.join(command)}' in directory: '{execution_path}'")

        try:
            # Execute the Maven command in the directory where the script was called.
            # - `capture_output=True` captures stdout and stderr.
            # - `text=True` decodes them as text using the default encoding.
            # - `shell=False` (the fix) is safer and passes arguments correctly.
            # - `cwd` ensures the command runs in the correct directory.
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                shell=False,
                encoding='utf-8',
                cwd=execution_path
            )

            # Combine stdout and stderr for a complete log.
            log_content = (
                f"--- MAVEN BUILD LOG ---\n\n"
                f"--- STDOUT ---\n{result.stdout}\n\n"
                f"--- STDERR ---\n{result.stderr}\n"
            )

            # Write the captured output to the log file.
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(log_content)

            print(f"INFO: Build logs have been saved to '{self.log_file}'.")

            # Check the return code to determine if the build was successful.
            if result.returncode != 0:
                print("\n########################################")
                print("ERROR: Maven build failed.")
                print(f"Please review the logs at: {self.log_file}")
                print("Aborting automation process.")
                print("########################################\n")
                sys.exit(1)  # Terminate the script on build failure.
            else:
                print("\n----------------------------------------")
                print("SUCCESS: Maven build completed successfully.")
                print("----------------------------------------\n")

        except FileNotFoundError:
            print("ERROR: The 'mvn' command was not found.")
            print("Please ensure that Apache Maven is installed and that its 'bin' directory is in your system's PATH.")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: An unexpected error occurred during the build: {e}")
            sys.exit(1)


def main():
    """
    The main function to orchestrate the automation tasks.
    """
    print("--- Developer Assistant: Git Push Automation (V1) ---")

    # Step 1: Build the Maven project using the MavenBuilder class.
    builder = MavenBuilder()
    builder.build()

    # If the script reaches this point, the build was successful.
    print("INFO: Proceeding to the next steps of the automation...")
    # Future features (like git commands) will be added here.


if __name__ == "__main__":
    main()
