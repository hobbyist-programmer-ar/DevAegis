import subprocess
import os
import tempfile
import sys
from typing import Optional

class MavenDependencyAnalyzer:
    """
    A Python class to fetch the dependency tree for a specific Maven project.

    This class works by running `mvn dependency:tree` on a `pom.xml`
    file in a specified directory (or the current working directory).

    Prerequisites:
    - The 'mvn' (Maven) command must be installed and accessible
      in your system's PATH.
    - A 'pom.xml' file must exist in the target directory.
    """

    # We no longer need the POM_TEMPLATE

    def __init__(self, mvn_executable: str = 'mvn'):
        """
        Initializes the analyzer.

        Args:
            mvn_executable: The name or path to the Maven executable.
                            Defaults to 'mvn', assuming it's in the PATH.
        """
        self.mvn_executable = mvn_executable
        self_check_result = self._check_maven()
        if not self_check_result["success"]:
            print(
                f"Warning: Maven check failed. "
                f"Error: {self_check_result['error']}",
                file=sys.stderr
            )
            print(
                "Please ensure 'mvn' is installed and in your system's PATH.",
                file=sys.stderr
            )

    def _check_maven(self) -> dict:
        """Checks if the mvn executable is available."""
        try:
            result = subprocess.run(
                [self.mvn_executable, '-v'],
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8'
            )
            return {"success": True, "output": result.stdout}
        except FileNotFoundError:
            return {"success": False, "error": f"Executable not found: {self.mvn_executable}"}
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": f"Maven version check failed: {e.stderr}"}

    def _parse_project_tree_output(self, output: str) -> str:
        """
        Parses the raw `mvn dependency:tree` output to extract
        only the project's dependency tree.
        """
        tree_lines = []
        capturing = False
        # Marker for the start of the dependency tree output
        start_marker = "[INFO] --- dependency"
        end_marker = "[INFO] ------------------------------------------------------------------------"
        print(output)
        for line in output.splitlines():
            if start_marker in line:
                capturing = True  # We've found the start of the tree output
                continue  # Skip this line

            if capturing:
                if line.startswith(end_marker):
                    # We've reached the end of the [INFO] block
                    break

                if line.startswith("[INFO] "):
                    # Add the line, but strip the [INFO] prefix
                    tree_lines.append(line[len("[INFO] "):])
                elif line.startswith("[WARNING]"):
                    # Include warnings as they can be important
                    tree_lines.append(line)
                elif not line.startswith("[INFO] BUILD SUCCESS"):
                     # Reached the end (e.g., BUILD SUCCESS)
                     break

        print (tree_lines)
        if not tree_lines:
            return "Could not parse dependency tree. Is 'pom.xml' valid?"

        # The tree_lines list now contains the project GAV and its tree
        return "\n".join(tree_lines)

    def get_project_dependency_tree(self, project_path: str = None) -> Optional[str]:
        """
        Fetches the dependency tree for a Maven project.

        Args:
            project_path: The file path to the project directory containing
                          the pom.xml. If None, defaults to the
                          current working directory.

        Returns:
            A string representing the dependency tree, or None on error.
        """
        if project_path is None:
            project_path = os.getcwd()

        pom_path = os.path.join(project_path, 'pom.xml')

        if not os.path.isfile(pom_path):
            print(f"Error: 'pom.xml' not found in {project_path}", file=sys.stderr)
            return None

        print(f"Fetching dependency tree for project at {pom_path}...")

        # Build the Maven command
        command = [
            self.mvn_executable,
            'dependency:tree',
            '-f', pom_path
        ]

        try:
            # Run the Maven command
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8'
            )

            # Parse the output
            return self._parse_project_tree_output(result.stdout)

        except FileNotFoundError:
                print(f"Error: Maven executable not found at '{self.mvn_executable}'.")
                print("Please install Maven and ensure it is in your system's PATH.")
                return None
        except subprocess.CalledProcessError as e:
                print(f"Error running Maven. Return code: {e.returncode}")
                print("\n--- Maven STDOUT ---")
                print(e.stdout)
                print("\n--- Maven STDERR ---")
                print(e.stderr)
                return None
        except Exception as e:
                print(f"An unexpected error occurred: {e}")
                return None

    def get_artifact_dependency_tree(self, group_id: str, artifact_id: str, project_path: str = None) -> Optional[str]:
        """
        Fetches the dependency tree for a specific artifact within a Maven project.
        This uses the project's pom.xml for context but filters the tree output.

        Args:
            group_id: The Group ID of the artifact to filter for.
            artifact_id: The Artifact ID of the artifact to filter for.
            project_path: The file path to the project directory containing
                          the pom.xml. If None, defaults to the
                          current working directory.

        Returns:
            A string representing the dependency tree for the specified
            artifact, or None on error.
        """
        if project_path is None:
            project_path = os.getcwd()

        pom_path = os.path.join(project_path, 'pom.xml')

        if not os.path.isfile(pom_path):
            print(f"Error: 'pom.xml' not found in {project_path}", file=sys.stderr)
            return None

        include_filter = f"{group_id}:{artifact_id}"
        print(f"Fetching dependency tree for artifact '{include_filter}'")
        print(f"using project context from {pom_path}...")

        # Build the Maven command with the -Dincludes filter
        command = [
            self.mvn_executable,
            'dependency:tree',
            '-f', pom_path,
            f'-Dincludes={include_filter}'
        ]

        try:
            # Run the Maven command
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8'
            )

            # We can reuse the same parser
            return self._parse_project_tree_output(result.stdout)

        except FileNotFoundError:
                print(f"Error: Maven executable not found at '{self.mvn_executable}'.")
                print("Please install Maven and ensure it is in your system's PATH.")
                return None
        except subprocess.CalledProcessError as e:
                print(f"Error running Maven. Return code: {e.returncode}")
                print("\n--- Maven STDOUT ---")
                print(e.stdout)
                print("\n--- Maven STDERR ---")
                print(e.stderr)
                return None
        except Exception as e:
                print(f"An unexpected error occurred: {e}")
                return None

# --- Example Usage ---
if __name__ == "__main__":
    # Create an instance of the analyzer
    analyzer = MavenDependencyAnalyzer()

    # # --- Example: Run on the current directory ---
    # print("\n" + "="*50)
    # print("Attempting to find dependency tree for project in")
    # print(f"current directory: {os.getcwd()}")
    # print("="*50)

    # # Note: This requires 'pom.xml' to be in the directory
    # # where this script is run.
    # tree = analyzer.get_project_dependency_tree()

    # if tree:
    #     print("\n--- Dependency Tree ---")
    #     print(tree)
    # else:
    #     print("\nCould not generate tree. Is 'pom.xml' present in this directory?")

    # --- Example 2: Run for a specific artifact in the current project ---
    # NOTE: This example will only work if 'junit:junit' is a
    # dependency in your pom.xml.
    # Change 'junit', 'junit' to an artifact in your project.
    print("\n" + "="*50)
    print("Attempting to find tree for 'junit:junit'")
    print(f"in project: {os.getcwd()}")
    print("="*50)

    artifact_tree = analyzer.get_artifact_dependency_tree('org.yaml', 'snakeyaml')


    if artifact_tree:
        print("\n--- Artifact Dependency Tree ---")
        print(artifact_tree)
    else:
        print("\nCould not generate tree for artifact.")
        print("Is 'junit:junit' a dependency in your 'pom.xml'?")
