"""
Containerized RPM utilities wrapper.
This module provides platform-independent RPM inspection by executing
rpm/rpmbuild commands inside a podman container instead of on the host.

Usage:
    from utils.rpmbuild_utils_containerized import ContainerizedRpmUtils
    
    # Initialize with a podman instance that has RPMs imported
    podman = DefaultPodman()
    podman.importAllRpms("rpms17el8")
    
    rpm_utils = ContainerizedRpmUtils(podman)
    
    # Use like regular rpmbuild_utils functions
    files = rpm_utils.listFilesInPackage("java-17-openjdk-17.0.16.0.8-2.el8.x86_64.rpm")
    requires = rpm_utils.listOfRequires("java-17-openjdk-17.0.16.0.8-2.el8.x86_64.rpm")
"""

import ntpath
import outputControl.logging_access as la
import config.verbosity_config as vc


class ContainerizedRpmUtils:
    """
    Wrapper class that provides containerized RPM utility functions.
    All RPM inspection commands are executed inside the podman container,
    making the framework platform-independent.
    """
    
    def __init__(self, podman_instance):
        """
        Initialize with a podman instance that has RPMs imported.
        
        Args:
            podman_instance: Instance of Podman class with RPMs already imported
        """
        self.podman = podman_instance
    
    def listFilesInPackage(self, rpmFile):
        """
        List files in an RPM package.
        
        Args:
            rpmFile (str): RPM filename or path
        
        Returns:
            list: List of file paths in the package
        """
        return self.podman.containerized_listFilesInPackage(rpmFile)
    
    def listDocsInPackage(self, rpmFile):
        """
        List documentation files in an RPM package.
        
        Args:
            rpmFile (str): RPM filename or path
        
        Returns:
            list: List of documentation file paths
        """
        return self.podman.containerized_listDocsInPackage(rpmFile)
    
    def listConfigFilesInPackage(self, rpmFile):
        """
        List config files in an RPM package.
        
        Args:
            rpmFile (str): RPM filename or path
        
        Returns:
            list: List of config file paths
        """
        return self.podman.containerized_listConfigFilesInPackage(rpmFile)
    
    def listOfRequires(self, rpmFile):
        """
        List package requirements.
        
        Args:
            rpmFile (str): RPM filename or path
        
        Returns:
            list: List of required packages
        """
        return self.podman.containerized_listOfRequires(rpmFile)
    
    def listOfProvides(self, rpmFile):
        """
        List package provides.
        
        Args:
            rpmFile (str): RPM filename or path
        
        Returns:
            list: List of provided packages/capabilities
        """
        return self.podman.containerized_listOfProvides(rpmFile)
    
    def listOfObsoletes(self, rpmFile):
        """
        List package obsoletes.
        
        Args:
            rpmFile (str): RPM filename or path
        
        Returns:
            list: List of obsoleted packages
        """
        return self.podman.containerized_listOfObsoletes(rpmFile)
    
    def listOfVersionlessRequires(self, rpmFile):
        """
        List package requirements without version information.
        
        Args:
            rpmFile (str): RPM filename or path
        
        Returns:
            list: List of required package names (without versions)
        """
        return self._filterVersions(self.listOfRequires(rpmFile))
    
    def listOfVersionlessProvides(self, rpmFile):
        """
        List package provides without version information.
        
        Args:
            rpmFile (str): RPM filename or path
        
        Returns:
            list: List of provided package names (without versions)
        """
        return self._filterVersions(self.listOfProvides(rpmFile))
    
    def listOfVersionlessObsoletes(self, rpmFile):
        """
        List package obsoletes without version information.
        
        Args:
            rpmFile (str): RPM filename or path
        
        Returns:
            list: List of obsoleted package names (without versions)
        """
        return self._filterVersions(self.listOfObsoletes(rpmFile))
    
    def getSrciplet(self, rpmFile, scripletId):
        """
        Extract scriptlet from RPM.
        
        Args:
            rpmFile (str): RPM filename or path
            scripletId (str): Scriptlet identifier (e.g., 'postinstall', 'preinstall')
        
        Returns:
            tuple: (executor, script_lines) where executor is the interpreter
                   and script_lines is a list of script content lines
        """
        return self.podman.containerized_getSrciplet(rpmFile, scripletId)
    
    def rpmbuildEval(self, macro):
        """
        Evaluate an RPM macro.
        
        Args:
            macro (str): Macro name to evaluate (without %{})
        
        Returns:
            str: Evaluated macro value
        """
        return self.podman.containerized_rpmbuildEval(macro)
    
    def _filterVersions(self, listOfStrings):
        """
        Filter version information from package names.
        
        Args:
            listOfStrings (list): List of package strings with versions
        
        Returns:
            list: List of package names without versions
        """
        filtered = []
        for orig in listOfStrings:
            if orig.strip():  # Skip empty lines
                filtered.append(orig.split()[0])
        return filtered


# Convenience function to create a containerized utils instance
def create_containerized_utils(podman_instance):
    """
    Create a ContainerizedRpmUtils instance.
    
    Args:
        podman_instance: Podman instance with RPMs imported
    
    Returns:
        ContainerizedRpmUtils: Utility instance
    """
    return ContainerizedRpmUtils(podman_instance)


# Example usage function
def example_usage():
    """
    Example of how to use containerized RPM utilities.
    """
    from utils.podman.podman_executor import DefaultPodman
    
    # Initialize podman and import RPMs
    podman = DefaultPodman()
    podman.importAllRpms("rpms17el8")
    
    # Create containerized utils
    rpm_utils = ContainerizedRpmUtils(podman)
    
    # Use the utilities
    rpm_file = "java-17-openjdk-17.0.16.0.8-2.el8.x86_64.rpm"
    
    print("Files in package:")
    files = rpm_utils.listFilesInPackage(rpm_file)
    for f in files[:10]:  # Print first 10
        print(f"  {f}")
    
    print("\nRequires:")
    requires = rpm_utils.listOfRequires(rpm_file)
    for req in requires[:10]:  # Print first 10
        print(f"  {req}")
    
    print("\nProvides:")
    provides = rpm_utils.listOfProvides(rpm_file)
    for prov in provides[:10]:  # Print first 10
        print(f"  {prov}")
    
    print("\nPostinstall scriptlet:")
    executor, script = rpm_utils.getSrciplet(rpm_file, "postinstall")
    print(f"  Executor: {executor}")
    print(f"  Script lines: {len(script)}")


if __name__ == "__main__":
    example_usage()

# Made with Bob
