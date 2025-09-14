from src.dev_aegis import vulnerability_fixer
from src.dev_aegis.builder import MavenBuilder
# from src.dev_aegis.analyser import SonarAnalyser
from src.dev_aegis.analyser import SnykAnalyser
from src.dev_aegis.gitter import GitChecker
from src.dev_aegis.vulnerability_fixer import VulnerabilityFixer

def main():
    builder = MavenBuilder()
    builder.build()
    # sonar_analyser = SonarAnalyser()
    # sonar_analyser.analyze()
    snyk_analyser = SnykAnalyser()
    snyk_analyser.analyze()
    vulnerability_fixer = VulnerabilityFixer()
    vulnerability_fixer.run()
    git_checker = GitChecker()
    git_checker.run_full_process()


if __name__ == "__main__":
    main()
