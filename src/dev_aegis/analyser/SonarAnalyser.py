import subprocess
import os
import sys
import xml.etree.ElementTree as ET
import time

class SonarAnalyser:
    """
    Handles SonarQube analysis by running the scanner, fetching results from the
    server, generating a report, and checking quality gates.
    """
    def __init__(self):
        """
        Initializes the SonarAnalyser, setting up paths and SonarQube properties.
        :param project_root: The absolute path to the maven project directory.
        """
        self.project_root = os.getcwd()
        self.report_dir = os.path.join(self.project_root, ".dev-aegis/analyser")
        self.report_file = os.path.join(self.report_dir, "sonar-report.md")
        self.log_file = os.path.join(self.report_dir, "sonar-scanner.log")
        self.jacoco_report_path = os.path.join(self.project_root, 'target', 'site', 'jacoco', 'jacoco.xml')
        self._ensure_report_directory_exists()

        self.sonarqube_url = None
        self.project_key = None
        # For authentication, set a SONAR_TOKEN environment variable.
        self.sonarqube_token = os.getenv('SONAR_TOKEN')
        self._parse_sonar_properties()

    def _ensure_report_directory_exists(self):
        """
        Creates the report directory if it doesn't already exist.
        """
        try:
            os.makedirs(self.report_dir, exist_ok=True)
            print(f"INFO: Report directory '{self.report_dir}' is ready.")
        except OSError as e:
            print(f"ERROR: Failed to create directory {self.report_dir}: {e}")
            sys.exit(1)

    def _parse_sonar_properties(self):
        """
        Parses 'sonar-project.properties' to get the server URL and project key.
        """
        properties_path = os.path.join(self.project_root, 'sonar-project.properties')
        try:
            with open(properties_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    key, value = line.split('=', 1)
                    if key.strip() == 'sonar.host.url':
                        self.sonarqube_url = value.strip()
                    elif key.strip() == 'sonar.projectKey':
                        self.project_key = value.strip()

            if not self.sonarqube_url or not self.project_key:
                print("ERROR: 'sonar.host.url' and/or 'sonar.projectKey' not found in sonar-project.properties.")
                sys.exit(1)
            print("INFO: SonarQube properties parsed successfully.")
        except FileNotFoundError:
            print(f"ERROR: 'sonar-project.properties' file not found at '{properties_path}'.")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: Failed to parse sonar-project.properties: {e}")
            sys.exit(1)

    def analyze(self):
        """
        Runs the sonar-scanner command and then processes the results from the server.
        """
        print("INFO: Starting SonarQube analysis...")
        command = ['sonar-scanner']
        print(f"INFO: Executing command: '{' '.join(command)}' in directory: '{self.project_root}'")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                shell=False,
                encoding='utf-8',
                cwd=self.project_root
            )

            log_content = f"--- SONAR-SCANNER LOG ---\n\n--- STDOUT ---\n{result.stdout}\n\n--- STDERR ---\n{result.stderr}\n"
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(log_content)
            print(f"INFO: Sonar Scanner logs saved to '{self.log_file}'.")

            if "EXECUTION SUCCESS" not in result.stdout:
                print("\n########################################")
                print("ERROR: Sonar Scanner execution failed.")
                print(f"Please review the scanner logs at: {self.log_file}")
                print("########################################\n")
                sys.exit(1)

            print("INFO: Sonar Scanner analysis submitted successfully.")
            # Add a delay to allow the server to process the report. A more robust solution
            # would be to poll the analysis task endpoint, but a simple wait is often sufficient.
            wait_time = 15
            print(f"INFO: Waiting for {wait_time} seconds for SonarQube server to process the analysis...")
            time.sleep(wait_time)

        except FileNotFoundError:
            print("ERROR: The 'sonar-scanner' command was not found.")
            print("Please ensure Sonar Scanner is installed and its 'bin' directory is in your system's PATH.")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: An unexpected error occurred during the scan: {e}")
            sys.exit(1)

        self._process_analysis_results()

    def _fetch_bug_counts(self):
        """
        Fetches Blocker and Critical bug counts from the SonarQube server API.
        Returns a tuple of (blocker_bugs, critical_bugs).
        """
        try:
            import requests
        except ImportError:
            print("\nERROR: The 'requests' library is required for this script. Please install it using: pip install requests\n")
            sys.exit(1)

        metric_keys = "blocker_violations,critical_violations"
        api_url = f"{self.sonarqube_url}/api/measures/component"
        params = {'component': self.project_key, 'metricKeys': metric_keys}
        auth = (self.sonarqube_token, '') if self.sonarqube_token else None

        print(f"INFO: Querying SonarQube API for bug counts...")
        try:
            response = requests.get(api_url, params=params, auth=auth)
            response.raise_for_status()  # Raise an exception for HTTP errors (e.g., 401, 404, 500)

            data = response.json()
            measures = {m['metric']: int(m['value']) for m in data.get('component', {}).get('measures', [])}

            blocker_bugs = measures.get('blocker_violations', 0)
            critical_bugs = measures.get('critical_violations', 0)

            print(f"INFO: Fetched from SonarQube - Blockers: {blocker_bugs}, Criticals: {critical_bugs}")
            return blocker_bugs, critical_bugs

        except requests.exceptions.RequestException as e:
            print(f"\nERROR: Failed to connect to SonarQube API: {e}")
            print("Please check the 'sonar.host.url', your network connection, and authentication token (SONAR_TOKEN).")
            return None, None
        except (KeyError, ValueError) as e:
            print(f"\nERROR: Could not parse SonarQube API response: {e}")
            print("The response from the server was not in the expected format.")
            return None, None

    def _parse_jacoco_report(self):
        """
        Parses the jacoco.xml report to extract code coverage percentage.
        Returns the coverage percentage as a float.
        """
        print(f"INFO: Attempting to parse JaCoCo report at '{self.jacoco_report_path}'...")
        try:
            tree = ET.parse(self.jacoco_report_path)
            root = tree.getroot()
            instruction_counter = root.find("./counter[@type='INSTRUCTION']")

            if instruction_counter is not None:
                missed = int(instruction_counter.get('missed'))
                covered = int(instruction_counter.get('covered'))
                total = missed + covered
                coverage = (covered / total) * 100 if total > 0 else 0.0
                print(f"INFO: JaCoCo instruction coverage found: {coverage:.2f}%")
                return coverage
            else:
                print("WARN: Could not find INSTRUCTION counter in JaCoCo report. Defaulting to 0% coverage.")
                return 0.0
        except FileNotFoundError:
            print(f"ERROR: JaCoCo report not found at '{self.jacoco_report_path}'. Cannot determine code coverage.")
            return 0.0
        except Exception as e:
            print(f"ERROR: Failed to parse JaCoCo XML report: {e}")
            return 0.0

    def _process_analysis_results(self):
        """
        Fetches remote and local reports, generates a combined report,
        and checks quality gates.
        """
        print("INFO: Processing analysis results...")
        coverage = self._parse_jacoco_report()
        blocker_bugs, critical_bugs = self._fetch_bug_counts()

        if blocker_bugs is None or critical_bugs is None:
            print("\nERROR: Could not retrieve bug counts from SonarQube. Aborting process.")
            sys.exit(1)

        failed = (blocker_bugs > 0) or (critical_bugs > 0) or (coverage < 80.0)
        status = "FAILED" if failed else "PASSED"

        # Generate the markdown report
        report_content = (
            f"# SonarQube Analysis Report\n\n"
            f"## Quality Gate Status: {status}\n\n"
            f"**Summary**\n"
            f"- Blocker Bugs: **{blocker_bugs}** (Threshold: 0) *(From SonarQube)*\n"
            f"- Critical Bugs: **{critical_bugs}** (Threshold: 0) *(From SonarQube)*\n"
            f"- Code Coverage: **{coverage:.2f}%** (Threshold: >80%) *(From JaCoCo)*\n"
        )

        with open(self.report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"INFO: Analysis report generated at '{self.report_file}'.")

        if failed:
            print("\n########################################")
            print("ERROR: Quality Gate FAILED. The code does not meet quality standards.")
            if blocker_bugs > 0 or critical_bugs > 0:
                print(f"- Found {blocker_bugs} Blocker and {critical_bugs} Critical bugs.")
            if coverage < 80.0:
                print(f"- Code coverage is {coverage:.2f}%, which is below the required 80%.")
            print(f"\nPlease review the full report at: {self.report_file}")
            print("Aborting automation process.")
            print("########################################\n")
            sys.exit(1)
        else:
            print("\n----------------------------------------")
            print("SUCCESS: Quality gate passed.")
            print("----------------------------------------\n")

def main():
    """
    The main function to orchestrate the automation tasks.
    """
    project_root = os.getcwd()
    print(f"--- Developer Assistant: SonarQube Analysis ---")
    print(f"--- Running in directory: {project_root} ---")

    # NOTE: It's assumed that 'mvn clean install' has been run prior to this script
    # to generate the necessary reports.

    # Run SonarQube analysis.
    analyser = SonarAnalyser()
    analyser.analyze()

    # If the script reaches this point, the analysis was successful.
    print("INFO: All quality checks passed.")


if __name__ == "__main__":
    main()
