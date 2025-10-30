"""
Dependency checker to verify required packages are installed
"""
import logging
import importlib.util

logger = logging.getLogger(__name__)


class DependencyChecker:
    """Check for required dependencies and provide helpful error messages"""
    
    # Map of provider names to their required packages
    PROVIDER_DEPENDENCIES = {
        'openai': ['openai'],
        'claude': ['anthropic'],
        'gemini': ['google.generativeai'],
        'ollama': ['ollama'],
    }
    
    # Core dependencies required for the application
    CORE_DEPENDENCIES = [
        'fastapi',
        'sqlalchemy',
        'uvicorn',
        'pydantic',
    ]
    
    @staticmethod
    def check_package(package_name: str) -> bool:
        """
        Check if a package is installed
        
        Args:
            package_name: Name of the package to check
            
        Returns:
            bool: True if package is installed, False otherwise
        """
        spec = importlib.util.find_spec(package_name)
        return spec is not None
    
    @staticmethod
    def check_core_dependencies() -> dict:
        """
        Check all core dependencies
        
        Returns:
            dict: Dictionary with dependency status
        """
        results = {}
        missing_deps = []
        
        for dep in DependencyChecker.CORE_DEPENDENCIES:
            is_installed = DependencyChecker.check_package(dep)
            results[dep] = is_installed
            if not is_installed:
                missing_deps.append(dep)
        
        if missing_deps:
            logger.error(
                f"Missing core dependencies: {', '.join(missing_deps)}. "
                f"Please run: pip install -r requirements.txt"
            )
        
        return results
    
    @staticmethod
    def check_provider_dependencies() -> dict:
        """
        Check provider-specific dependencies
        
        Returns:
            dict: Dictionary with provider dependency status
        """
        results = {}
        
        for provider, packages in DependencyChecker.PROVIDER_DEPENDENCIES.items():
            provider_status = {}
            for package in packages:
                is_installed = DependencyChecker.check_package(package)
                provider_status[package] = is_installed
                if not is_installed:
                    logger.warning(
                        f"Provider '{provider}' dependency '{package}' is not installed. "
                        f"The provider will not be available until you run: pip install -r requirements.txt"
                    )
            results[provider] = provider_status
        
        return results
    
    @staticmethod
    def verify_all_dependencies() -> tuple[bool, list]:
        """
        Verify all dependencies and return status
        
        Returns:
            tuple: (all_core_installed, missing_providers)
        """
        logger.info("Checking dependencies...")
        
        # Check core dependencies
        core_results = DependencyChecker.check_core_dependencies()
        all_core_installed = all(core_results.values())
        
        # Check provider dependencies
        provider_results = DependencyChecker.check_provider_dependencies()
        missing_providers = [
            provider for provider, packages in provider_results.items()
            if not all(packages.values())
        ]
        
        if all_core_installed:
            logger.info("All core dependencies are installed")
        else:
            logger.error("Some core dependencies are missing")
        
        if missing_providers:
            logger.warning(
                f"Some providers have missing dependencies: {', '.join(missing_providers)}"
            )
        else:
            logger.info("All provider dependencies are installed")
        
        return all_core_installed, missing_providers
    
    @staticmethod
    def get_installation_help_message(provider: str = None) -> str:
        """
        Get a helpful message for installing dependencies
        
        Args:
            provider: Optional provider name for specific help
            
        Returns:
            str: Help message
        """
        if provider and provider in DependencyChecker.PROVIDER_DEPENDENCIES:
            packages = DependencyChecker.PROVIDER_DEPENDENCIES[provider]
            return (
                f"The '{provider}' provider requires the following packages: {', '.join(packages)}.\n"
                f"To install all dependencies, run: pip install -r requirements.txt"
            )
        else:
            return (
                "Some dependencies are missing. "
                "To install all required dependencies, run: pip install -r requirements.txt"
            )
