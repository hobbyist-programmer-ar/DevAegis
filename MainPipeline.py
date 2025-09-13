from src.dev_aegis.builder import MavenBuilder
# from src.dev_aegis.analyser import SonarAnalyser
from src.dev_aegis.analyser import SnykAnalyser
from src.dev_aegis.gitter import GitChecker

def main():
    builder = MavenBuilder()
    builder.build()
    # sonar_analyser = SonarAnalyser()
    # sonar_analyser.analyze()
    snyk_analyser = SnykAnalyser()
    snyk_analyser.analyze()
    git_checker = GitChecker()
    git_checker.run_full_process()


if __name__ == "__main__":
    main()
