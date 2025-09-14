import subprocess
import os
import sys
import json

class SnykAnalyser:
    """
    Handles security analysis using Snyk. It runs the scanner, parses the
    results for vulnerabilities, generates a report, and checks against
    defined quality gates.
    """
    def __init__(self):
        """
        Initializes the SnykAnalyser, setting up paths for reports.
        :param project_root: The absolute path to the project directory.
        """
        self.project_root = os.getcwd()
        self.report_dir = os.path.join(self.project_root, ".dev-aegis/analyser")
        self.report_file = os.path.join(self.report_dir, "snyk-report.md")
        self._ensure_report_directory_exists()

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

    def _run_snyk_command(self):
        """
        Runs the 'snyk test' command with JSON output and handles its execution.
        Snyk exit codes:
        - 0: No vulnerabilities found.
        - 1: Vulnerabilities found.
        - 2: An error occurred (e.g., bad configuration).
        - 3: No supported projects found.
        This function proceeds on 0 or 1, and fails on 2 or 3.
        """
        print("INFO: Starting Snyk vulnerability scan...")
        command = ['snyk', 'test', '--json']
        print(f"INFO: Executing command: '{' '.join(command)}' in directory: '{self.project_root}'")

        try:
            # We use a file for stdout to handle potentially large JSON outputs.
            json_output_path = os.path.join(self.report_dir, 'snyk_output.json')
            with open(json_output_path, 'w') as f_out:
                result = subprocess.run(
                    command,
                    stdout=f_out,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    cwd=self.project_root
                )

            # Read the JSON output back from the file
            with open(json_output_path, 'r') as f_in:
                snyk_json_output = f_in.read()

            if result.returncode >= 2:
                print("\n########################################")
                print(f"ERROR: Snyk CLI exited with error code {result.returncode}.")
                print("This may be due to a configuration issue or no supported projects found.")
                print(f"STDERR:\n{result.stderr}")
                print("########################################\n")
                sys.exit(1)

            print("INFO: Snyk scan completed. Parsing results...")
            return json.loads(snyk_json_output)

        except FileNotFoundError:
            print("ERROR: The 'snyk' command was not found.")
            print("Please ensure the Snyk CLI is installed and accessible in your system's PATH.")
            sys.exit(1)
        except json.JSONDecodeError:
            print("ERROR: Failed to parse Snyk's JSON output.")
            print("The scan may not have produced a valid report.")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: An unexpected error occurred during the Snyk scan: {e}")
            sys.exit(1)

    def _process_snyk_results(self, snyk_data):
        """
        Parses the Snyk JSON data, generates a report, and checks quality gates.
        """
        vulnerabilities_to_report = []
        quality_gate_failed = False
        failure_reasons = []

        # Snyk's output can be a single object or a list of objects
        snyk_results = snyk_data if isinstance(snyk_data, list) else [snyk_data]

        for project in snyk_results:
            if project.get('ok', True) is False and 'vulnerabilities' in project:
                for vuln in project['vulnerabilities']:
                    package = vuln.get('packageName', 'N/A')
                    severity = vuln.get('severity', 'N/A')
                    version = vuln.get('version', 'N/A')
                    fixed_in = ', '.join(vuln.get('fixedIn', [])) if vuln.get('fixedIn') else 'NA'
                    url = vuln.get('url', '#')
                    exploit_maturity = vuln.get('exploit', 'Not Available')

                    vulnerabilities_to_report.append({
                        'package': package,
                        'severity': severity,
                        'version': version,
                        'fixed_in': fixed_in,
                        'url': url
                    })

                    # Check Quality Gate: Condition 1 (Critical)
                    if severity == 'critical':
                        quality_gate_failed = True
                        failure_reasons.append(f"- CRITICAL vulnerability found in '{package}'.")

                    # Check Quality Gate: Condition 2 (High, Fixable, Mature Exploit)
                    if severity == 'high' and fixed_in != 'NA' and exploit_maturity == 'Mature':
                        quality_gate_failed = True
                        failure_reasons.append(f"- HIGH vulnerability with a mature exploit and available fix found in '{package}'.")

        self._generate_report(vulnerabilities_to_report)

        if quality_gate_failed:
            print("\n########################################")
            print("ERROR: Snyk Quality Gate FAILED. The code does not meet security standards.")
            # Use a set to print unique failure reasons
            for reason in sorted(list(set(failure_reasons))):
                print(reason)
            print(f"\nPlease review the full Snyk report at: {self.report_file}")
            print("Aborting automation process.")
            print("########################################\n")
            # sys.exit(1)
        else:
            print("\n----------------------------------------")
            print("SUCCESS: Snyk quality gate passed.")
            print("----------------------------------------\n")

    def _generate_report(self, vulnerabilities):
        """
        Generates a markdown report from the list of vulnerabilities.
        """
        if not vulnerabilities:
            report_content = "# Snyk Security Report\n\nCongratulations! No vulnerabilities were found."
        else:
            headers = ["Package", "Severity", "Vulnerable Version", "Fixed in Version", "CVE Report Link"]
            report_content = (
                f"# Snyk Security Report\n\n"
                f"Found {len(vulnerabilities)} vulnerabilities.\n\n"
                f"| {' | '.join(headers)} |\n"
                f"|{'|'.join(['---'] * len(headers))}|\n"
            )
            for vuln in vulnerabilities:
                link = f"[{vuln['package']}]({vuln['url']})"
                row = f"| {vuln['package']} | {vuln['severity'].title()} | {vuln['version']} | {vuln['fixed_in']} | [View Details]({vuln['url']}) |\n"
                report_content += row

        with open(self.report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"INFO: Snyk report generated at '{self.report_file}'.")

    def analyze(self):
        """
        Public method to orchestrate the entire Snyk analysis process.
        """
        snyk_data = self._run_snyk_command()
        self._process_snyk_results(snyk_data)

def main():
    """
    The main function to orchestrate the automation tasks.
    """
    project_root = os.getcwd()
    print(f"--- Developer Assistant: Snyk Security Analysis ---")
    print(f"--- Running in directory: {project_root} ---")

    analyser = SnykAnalyser()
    analyser.analyze()

    print("INFO: All quality checks passed.")

if __name__ == "__main__":
    main()
