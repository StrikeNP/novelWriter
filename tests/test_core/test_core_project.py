"""
novelWriter – NWProject Class Tester
====================================

This file is a part of novelWriter
Copyright 2018–2023, Veronica Berglyd Olsen

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

from PyQt5.QtWidgets import QMessageBox
import pytest

from shutil import copyfile
from zipfile import ZipFile

from mocked import causeOSError
from tools import C, cmpFiles, buildTestProject, XML_IGNORE

from novelwriter import CONFIG, SHARED
from novelwriter.enum import nwItemClass
from novelwriter.constants import nwFiles
from novelwriter.core.tree import NWTree
from novelwriter.core.index import NWIndex
from novelwriter.core.project import NWProject
from novelwriter.core.options import OptionState
from novelwriter.core.projectxml import ProjectXMLReader, ProjectXMLWriter, XMLReadState


@pytest.mark.core
def testCoreProject_NewRoot(fncPath, tstPaths, mockGUI, mockRnd):
    """Check that new root folders can be added to the project."""
    projFile = fncPath / "nwProject.nwx"
    testFile = tstPaths.outDir / "coreProject_NewRoot_nwProject.nwx"
    compFile = tstPaths.refDir / "coreProject_NewRoot_nwProject.nwx"

    theProject = NWProject()
    mockRnd.reset()
    buildTestProject(theProject, fncPath)

    assert theProject.newRoot(nwItemClass.NOVEL) == "0000000000010"
    assert theProject.newRoot(nwItemClass.PLOT) == "0000000000011"
    assert theProject.newRoot(nwItemClass.CHARACTER) == "0000000000012"
    assert theProject.newRoot(nwItemClass.WORLD) == "0000000000013"
    assert theProject.newRoot(nwItemClass.TIMELINE) == "0000000000014"
    assert theProject.newRoot(nwItemClass.OBJECT) == "0000000000015"
    assert theProject.newRoot(nwItemClass.CUSTOM) == "0000000000016"
    assert theProject.newRoot(nwItemClass.CUSTOM) == "0000000000017"

    assert theProject.projChanged is True
    assert theProject.saveProject() is True
    theProject.closeProject()

    copyfile(projFile, testFile)
    assert cmpFiles(testFile, compFile, ignoreStart=XML_IGNORE)
    assert theProject.projChanged is False

    # Delete the new items
    assert theProject.removeItem("0000000000010") is True
    assert theProject.removeItem("0000000000011") is True
    assert theProject.removeItem("0000000000012") is True
    assert theProject.removeItem("0000000000013") is True
    assert theProject.removeItem("0000000000014") is True
    assert theProject.removeItem("0000000000015") is True
    assert theProject.removeItem("0000000000016") is True
    assert theProject.removeItem("0000000000017") is True

    assert "0000000000010" not in theProject.tree
    assert "0000000000011" not in theProject.tree
    assert "0000000000012" not in theProject.tree
    assert "0000000000013" not in theProject.tree
    assert "0000000000014" not in theProject.tree
    assert "0000000000015" not in theProject.tree
    assert "0000000000016" not in theProject.tree
    assert "0000000000017" not in theProject.tree

# END Test testCoreProject_NewRoot


@pytest.mark.core
def testCoreProject_NewFileFolder(monkeypatch, fncPath, tstPaths, mockGUI, mockRnd):
    """Check that new files can be added to the project."""
    projFile = fncPath / "nwProject.nwx"
    testFile = tstPaths.outDir / "coreProject_NewFileFolder_nwProject.nwx"
    compFile = tstPaths.refDir / "coreProject_NewFileFolder_nwProject.nwx"

    theProject = NWProject()
    mockRnd.reset()
    buildTestProject(theProject, fncPath)

    # Invalid call
    assert theProject.newFolder("New Folder", "1234567890abc") is None
    assert theProject.newFile("New File", "1234567890abc") is None

    # Add files properly
    assert theProject.newFolder("Stuff", C.hNovelRoot) == "0000000000010"
    assert theProject.newFile("Hello", "0000000000010") == "0000000000011"
    assert theProject.newFile("Jane", C.hCharRoot) == "0000000000012"

    assert "0000000000010" in theProject.tree
    assert "0000000000011" in theProject.tree
    assert "0000000000012" in theProject.tree

    # Write to file, failed
    assert theProject.writeNewFile("blabla", 1, True) is False         # Not a handle
    assert theProject.writeNewFile("0000000000010", 1, True) is False  # Not a file
    assert theProject.writeNewFile(C.hTitlePage, 1, True) is False  # Already has content

    # Write to file, success
    assert theProject.writeNewFile("0000000000011", 2, True) is True
    assert theProject.storage.getDocument("0000000000011").readDocument() == "## Hello\n\n"

    # Write to file with additional text, success
    assert theProject.writeNewFile("0000000000012", 1, False, "Hi Jane\n\n") is True
    assert theProject.storage.getDocument("0000000000012").readDocument() == (
        "# Jane\n\nHi Jane\n\n"
    )

    # Save, close and check
    assert theProject.projChanged is True
    assert theProject.saveProject() is True

    copyfile(projFile, testFile)
    assert cmpFiles(testFile, compFile, ignoreStart=XML_IGNORE)
    assert theProject.projChanged is False

    # Delete new file, but block access
    with monkeypatch.context() as mp:
        mp.setattr("pathlib.Path.unlink", causeOSError)
        assert theProject.removeItem("0000000000011") is False
        assert "0000000000011" in theProject.tree

    # Delete new files and folders
    assert (fncPath / "content" / "0000000000012.nwd").exists()
    assert (fncPath / "content" / "0000000000011.nwd").exists()

    assert theProject.removeItem("0000000000012") is True
    assert theProject.removeItem("0000000000011") is True
    assert theProject.removeItem("0000000000010") is True

    assert not (fncPath / "content" / "0000000000012.nwd").exists()
    assert not (fncPath / "content" / "0000000000011.nwd").exists()

    assert "0000000000010" not in theProject.tree
    assert "0000000000011" not in theProject.tree
    assert "0000000000012" not in theProject.tree

    theProject.closeProject()

# END Test testCoreProject_NewFileFolder


@pytest.mark.core
def testCoreProject_Open(monkeypatch, caplog, mockGUI, fncPath, mockRnd):
    """Test opening a project."""
    theProject = NWProject()
    mockRnd.reset()
    buildTestProject(theProject, fncPath)

    # Initialising the storage class fails
    with monkeypatch.context() as mp:
        mp.setattr("novelwriter.core.storage.NWStorage.openProjectInPlace", lambda *a, **k: False)
        assert theProject.openProject(fncPath) is False

    # Fail on lock file
    theProject.storage._lockFilePath = fncPath / nwFiles.PROJ_LOCK
    assert theProject.storage.writeLockFile() is True
    assert theProject.openProject(fncPath) is False
    assert isinstance(theProject.lockStatus, list)

    # Fail to read lockfile (which still opens the project)
    with monkeypatch.context() as mp:
        mp.setattr("novelwriter.core.storage.NWStorage.readLockFile", lambda *a: ["ERROR"])
        caplog.clear()
        assert theProject.openProject(fncPath) is True
        assert "Failed to check lock file" in caplog.text
        theProject.closeProject()

    # Force open with lockfile
    theProject.storage._lockFilePath = fncPath / nwFiles.PROJ_LOCK
    assert theProject.storage.writeLockFile() is True
    assert theProject.openProject(fncPath, clearLock=True) is True
    theProject.closeProject()
    assert theProject.lockStatus is None

    # Fail getting xml reader
    with monkeypatch.context() as mp:
        mp.setattr("novelwriter.core.storage.NWStorage.getXmlReader", lambda *a: None)
        assert theProject.openProject(fncPath) is False

    # Not a novelwriter XML file
    with monkeypatch.context() as mp:
        mp.setattr(ProjectXMLReader, "read", lambda *a: False)
        mp.setattr(ProjectXMLReader, "state", property(lambda *a: XMLReadState.NOT_NWX_FILE))
        assert theProject.openProject(fncPath) is False
        lastMsg = SHARED.alert.logMessage if SHARED.alert else ""
        assert "Project file does not appear" in lastMsg

    # Unknown project file version
    with monkeypatch.context() as mp:
        mp.setattr(ProjectXMLReader, "read", lambda *a: False)
        mp.setattr(ProjectXMLReader, "state", property(lambda *a: XMLReadState.UNKNOWN_VERSION))
        assert theProject.openProject(fncPath) is False
        lastMsg = SHARED.alert.logMessage if SHARED.alert else ""
        assert "Unknown or unsupported novelWriter project file" in lastMsg

    # Other parse error
    with monkeypatch.context() as mp:
        mp.setattr(ProjectXMLReader, "read", lambda *a: False)
        mp.setattr(ProjectXMLReader, "state", property(lambda *a: XMLReadState.CANNOT_PARSE))
        assert theProject.openProject(fncPath) is False
        lastMsg = SHARED.alert.logMessage if SHARED.alert else ""
        assert "Failed to parse project xml" in lastMsg

    # Won't convert legacy file
    with monkeypatch.context() as mp:
        mp.setattr(ProjectXMLReader, "state", property(lambda *a: XMLReadState.WAS_LEGACY))
        mp.setattr(QMessageBox, "result", lambda *a: QMessageBox.No)
        assert theProject.openProject(fncPath) is False
        lastMsg = SHARED.alert.logMessage if SHARED.alert else ""
        assert "The file format of your project is about to be" in lastMsg

    # Won't open project from newer version
    with monkeypatch.context() as mp:
        mp.setattr(ProjectXMLReader, "hexVersion", property(lambda *a: 0x99999999))
        mp.setattr(QMessageBox, "result", lambda *a: QMessageBox.No)
        assert theProject.openProject(fncPath) is False
        lastMsg = SHARED.alert.logMessage if SHARED.alert else ""
        assert "This project was saved by a newer version" in lastMsg

    # Fail checking items should still pass
    with monkeypatch.context() as mp:
        mp.setattr("novelwriter.core.tree.NWTree.updateItemData", lambda *a: False)
        assert theProject.openProject(fncPath) is True

    theProject.closeProject()

    # Trigger an index rebuild
    with monkeypatch.context() as mp:
        mp.setattr(ProjectXMLReader, "state", property(lambda *a: XMLReadState.WAS_LEGACY))
        mp.setattr("novelwriter.core.index.NWIndex.loadIndex", lambda *a: True)
        theProject.index._indexBroken = True
        assert theProject.openProject(fncPath) is True
        lastMsg = SHARED.alert.logMessage if SHARED.alert else ""
        assert "The file format of your project is about to be" in lastMsg
        assert theProject.index._indexBroken is False

    theProject.closeProject()

# END Test testCoreProject_Open


@pytest.mark.core
def testCoreProject_Save(monkeypatch, mockGUI, mockRnd, fncPath):
    """Test saving a project."""
    theProject = NWProject()

    # Nothing to save
    assert theProject.saveProject() is False

    mockRnd.reset()
    buildTestProject(theProject, fncPath)

    # Fail getting xml writer
    with monkeypatch.context() as mp:
        mp.setattr("novelwriter.core.storage.NWStorage.getXmlWriter", lambda *a: None)
        assert theProject.saveProject() is False

    # Fail writing
    with monkeypatch.context() as mp:
        mp.setattr(ProjectXMLWriter, "write", lambda *a: False)
        assert theProject.saveProject() is False

    # Save with and without autosave
    assert theProject.saveProject(autoSave=False) is True
    assert theProject.saveProject(autoSave=True) is True
    theProject.closeProject()

# END Test testCoreProject_Save


@pytest.mark.core
def testCoreProject_AccessItems(mockGUI, fncPath, mockRnd):
    """Test helper functions for the project folder."""
    theProject = NWProject()
    buildTestProject(theProject, fncPath)

    # Storage Objects
    assert isinstance(theProject.index, NWIndex)
    assert isinstance(theProject.tree, NWTree)
    assert isinstance(theProject.options, OptionState)

    # Move Novel ROOT to after its files
    oldOrder = [
        C.hNovelRoot,
        C.hPlotRoot,
        C.hCharRoot,
        C.hWorldRoot,
        C.hTitlePage,
        C.hChapterDir,
        C.hChapterDoc,
        C.hSceneDoc,
    ]
    newOrder = [
        C.hTitlePage,
        C.hChapterDoc,
        C.hSceneDoc,
        C.hChapterDir,
        C.hNovelRoot,
        C.hPlotRoot,
        C.hCharRoot,
        C.hWorldRoot,
    ]
    assert theProject.tree.handles() == oldOrder
    theProject.setTreeOrder(newOrder)
    assert theProject.tree.handles() == newOrder

    # Add a non-existing item
    theProject.tree._order.append(C.hInvalid)

    # Add an item with a non-existent parent
    nHandle = theProject.newFile("Test File", C.hChapterDir)
    theProject.tree[nHandle].setParent("cba9876543210")
    assert theProject.tree[nHandle].itemParent == "cba9876543210"

    retOrder = []
    for tItem in theProject.iterProjectItems():
        retOrder.append(tItem.itemHandle)

    assert retOrder == [
        C.hNovelRoot,
        C.hPlotRoot,
        C.hCharRoot,
        C.hWorldRoot,
        nHandle,
        C.hTitlePage,
        C.hChapterDir,
        C.hChapterDoc,
        C.hSceneDoc,
    ]
    assert theProject.tree[nHandle].itemParent is None

# END Test testCoreProject_AccessItems


@pytest.mark.core
def testCoreProject_StatusImport(mockGUI, fncPath, mockRnd):
    """Test the status and importance flag handling."""
    theProject = NWProject()
    mockRnd.reset()
    buildTestProject(theProject, fncPath)

    statusKeys = [C.sNew, C.sNote, C.sDraft, C.sFinished]
    importKeys = [C.iNew, C.iMinor, C.iMajor, C.iMain]

    # Change Status
    # =============

    theProject.tree[C.hNovelRoot].setStatus(statusKeys[3])
    theProject.tree[C.hPlotRoot].setStatus(statusKeys[2])
    theProject.tree[C.hCharRoot].setStatus(statusKeys[1])
    theProject.tree[C.hWorldRoot].setStatus(statusKeys[3])

    assert theProject.tree[C.hNovelRoot].itemStatus == statusKeys[3]
    assert theProject.tree[C.hPlotRoot].itemStatus == statusKeys[2]
    assert theProject.tree[C.hCharRoot].itemStatus == statusKeys[1]
    assert theProject.tree[C.hWorldRoot].itemStatus == statusKeys[3]

    newList = [
        {"key": statusKeys[0], "name": "New", "cols": (1, 1, 1)},
        {"key": statusKeys[1], "name": "Draft", "cols": (2, 2, 2)},   # These are swapped
        {"key": statusKeys[2], "name": "Note", "cols": (3, 3, 3)},    # These are swapped
        {"key": statusKeys[3], "name": "Edited", "cols": (4, 4, 4)},  # Renamed
        {"key": None, "name": "Finished", "cols": (5, 5, 5)},         # New, reused name
    ]
    assert theProject.setStatusColours(None, None) is False
    assert theProject.setStatusColours([], []) is False
    assert theProject.setStatusColours(newList, []) is True

    assert theProject.data.itemStatus.name(statusKeys[0]) == "New"
    assert theProject.data.itemStatus.name(statusKeys[1]) == "Draft"
    assert theProject.data.itemStatus.name(statusKeys[2]) == "Note"
    assert theProject.data.itemStatus.name(statusKeys[3]) == "Edited"
    assert theProject.data.itemStatus.cols(statusKeys[0]) == (1, 1, 1)
    assert theProject.data.itemStatus.cols(statusKeys[1]) == (2, 2, 2)
    assert theProject.data.itemStatus.cols(statusKeys[2]) == (3, 3, 3)
    assert theProject.data.itemStatus.cols(statusKeys[3]) == (4, 4, 4)

    # Check the new entry
    lastKey = theProject.data.itemStatus.check("s000010")
    assert lastKey == "s000010"
    assert theProject.data.itemStatus.name(lastKey) == "Finished"
    assert theProject.data.itemStatus.cols(lastKey) == (5, 5, 5)

    # Delete last entry
    assert theProject.setStatusColours([], [lastKey]) is True
    assert theProject.data.itemStatus.name(lastKey) == "New"

    # Change Importance
    # =================

    fHandle = theProject.newFile("Jane Doe", C.hCharRoot)
    theProject.tree[fHandle].setImport(importKeys[3])

    assert theProject.tree[fHandle].itemImport == importKeys[3]
    newList = [
        {"key": importKeys[0], "name": "New", "cols": (1, 1, 1)},
        {"key": importKeys[1], "name": "Minor", "cols": (2, 2, 2)},
        {"key": importKeys[2], "name": "Major", "cols": (3, 3, 3)},
        {"key": importKeys[3], "name": "Min", "cols": (4, 4, 4)},
        {"key": None, "name": "Max", "cols": (5, 5, 5)},
    ]
    assert theProject.setImportColours(None, None) is False
    assert theProject.setImportColours([], []) is False
    assert theProject.setImportColours(newList, []) is True

    assert theProject.data.itemImport.name(importKeys[0]) == "New"
    assert theProject.data.itemImport.name(importKeys[1]) == "Minor"
    assert theProject.data.itemImport.name(importKeys[2]) == "Major"
    assert theProject.data.itemImport.name(importKeys[3]) == "Min"
    assert theProject.data.itemImport.cols(importKeys[0]) == (1, 1, 1)
    assert theProject.data.itemImport.cols(importKeys[1]) == (2, 2, 2)
    assert theProject.data.itemImport.cols(importKeys[2]) == (3, 3, 3)
    assert theProject.data.itemImport.cols(importKeys[3]) == (4, 4, 4)

    # Check the new entry
    lastKey = theProject.data.itemImport.check("i000012")
    assert lastKey == "i000012"
    assert theProject.data.itemImport.name(lastKey) == "Max"
    assert theProject.data.itemImport.cols(lastKey) == (5, 5, 5)

    # Delete last entry
    assert theProject.setImportColours([], [lastKey]) is True
    assert theProject.data.itemImport.name(lastKey) == "New"

    # Delete Status/Import
    # ====================

    theProject.data.itemStatus.resetCounts()
    for key in list(theProject.data.itemStatus.keys()):
        assert theProject.data.itemStatus.remove(key) is True

    theProject.data.itemImport.resetCounts()
    for key in list(theProject.data.itemImport.keys()):
        assert theProject.data.itemImport.remove(key) is True

    assert len(theProject.data.itemStatus) == 0
    assert len(theProject.data.itemImport) == 0
    assert theProject.saveProject() is True
    theProject.closeProject()

# END Test testCoreProject_StatusImport


@pytest.mark.core
def testCoreProject_Methods(monkeypatch, mockGUI, fncPath, mockRnd):
    """Test other project class methods and functions."""
    theProject = NWProject()
    buildTestProject(theProject, fncPath)

    # Project Name
    theProject.data.setName("  A Name ")
    assert theProject.data.name == "A Name"

    # Project Title
    theProject.data.setTitle("  A Title ")
    assert theProject.data.title == "A Title"

    # Project Author
    theProject.data.setAuthor("  Jane\tDoe ")
    assert theProject.data.author == "Jane Doe"

    # Edit Time
    theProject.data.setEditTime(1234)
    theProject._session._start = 1600000000
    with monkeypatch.context() as mp:
        mp.setattr("novelwriter.core.project.time", lambda: 1600005600)
        assert theProject.currentEditTime == 6834

    # Trash folder
    # Should create on first call, and just returned on later calls
    hTrash = "0000000000010"
    assert theProject.tree[hTrash] is None
    assert theProject.trashFolder() == hTrash
    assert theProject.trashFolder() == hTrash

    # Spell check
    theProject.setProjectChanged(False)
    theProject.data.setSpellCheck(True)
    theProject.data.setSpellCheck(False)
    assert theProject.projChanged is True
    assert theProject.projOpened > 0

    # Spell language
    theProject.setProjectChanged(False)
    assert theProject.data.spellLang is None
    theProject.data.setSpellLang(None)
    assert theProject.data.spellLang is None
    theProject.data.setSpellLang("None")  # Should be interpreted as None
    assert theProject.data.spellLang is None
    theProject.data.setSpellLang("en_GB")
    assert theProject.data.spellLang == "en_GB"
    assert theProject.projChanged is True

    # Project Language
    theProject.setProjectChanged(False)
    theProject.data.setLanguage("en")
    theProject.setProjectLang(None)
    assert theProject.data.language is None
    theProject.setProjectLang("en_GB")
    assert theProject.data.language == "en_GB"

    # Language Lookup
    assert theProject.localLookup(1) == "One"
    assert theProject.localLookup(10) == "Ten"

    # Set invalid language
    theProject.data.setLanguage("foo")
    theProject._loadProjectLocalisation()
    assert theProject.localLookup(1) == "One"
    assert theProject.localLookup(10) == "Ten"

    # Block reading language data
    theProject.data.setLanguage("en")
    with monkeypatch.context() as mp:
        mp.setattr("builtins.open", causeOSError)
        theProject._loadProjectLocalisation()
        assert theProject.localLookup(1) == "One"
        assert theProject.localLookup(10) == "Ten"

    # Last edited
    theProject.setProjectChanged(False)
    theProject._data.setLastHandle("0123456789abc", "editor")
    assert theProject._data.getLastHandle("editor") == "0123456789abc"
    assert theProject.projChanged

    # Last viewed
    theProject.setProjectChanged(False)
    theProject._data.setLastHandle("0123456789abc", "viewer")
    assert theProject._data.getLastHandle("viewer") == "0123456789abc"
    assert theProject.projChanged

    # Autoreplace
    theProject.setProjectChanged(False)
    theProject.data.setAutoReplace({"A": "B", "C": "D"})
    assert theProject.data.autoReplace == {"A": "B", "C": "D"}
    assert theProject.projChanged

    # Change project tree order
    oldOrder = [
        "0000000000008", "0000000000009", "000000000000a",
        "000000000000b", "000000000000c", "000000000000d",
        "000000000000e", "000000000000f", "0000000000010",
    ]
    newOrder = [
        "000000000000b", "000000000000c", "000000000000d",
        "0000000000008", "0000000000009", "000000000000a",
        "000000000000e", "000000000000f",
    ]
    assert theProject.tree.handles() == oldOrder
    theProject.setTreeOrder(newOrder)
    assert theProject.tree.handles() == newOrder
    theProject.setTreeOrder(oldOrder)
    assert theProject.tree.handles() == oldOrder

# END Test testCoreProject_Methods


@pytest.mark.core
def testCoreProject_Backup(monkeypatch, mockGUI, fncPath, tstPaths):
    """Test the automated backup feature of the project class. The test
    creates a backup of the Minimal test project, and then unzips the
    backup file and checks that the project XML file is identical to
    the original file.
    """
    theProject = NWProject()

    # No Project
    assert theProject.backupProject(doNotify=False) is False

    buildTestProject(theProject, fncPath)

    # Invalid Settings
    # ================

    # Missing project name
    CONFIG._backupPath = tstPaths.tmpDir
    theProject.data.setName("")
    assert theProject.backupProject(doNotify=False) is False

    # Valid Settings
    # ==============
    CONFIG._backupPath = tstPaths.tmpDir
    theProject.data.setName("Test Minimal")

    # Can't make folder
    with monkeypatch.context() as mp:
        mp.setattr("pathlib.Path.mkdir", causeOSError)
        assert theProject.backupProject(doNotify=False) is False

    # Can't write archive
    with monkeypatch.context() as mp:
        mp.setattr("zipfile.ZipFile.write", causeOSError)
        assert theProject.backupProject(doNotify=False) is False

    # Test correct settings
    assert theProject.backupProject(doNotify=True) is True

    theFiles = sorted((tstPaths.tmpDir / "Test Minimal").iterdir())
    assert len(theFiles) in (1, 2)  # Sometimes 2 due to clock tick

    theZip = theFiles[0]
    assert theZip.name.startswith("Test Minimal")
    assert theZip.suffix == ".zip"

    # Extract the archive
    with ZipFile(tstPaths.tmpDir / "Test Minimal" / theZip.name, mode="r") as inZip:
        inZip.extractall(tstPaths.tmpDir / "extract")

    # Check that the main project file was restored
    assert cmpFiles(
        fncPath / "nwProject.nwx",
        tstPaths.tmpDir / "extract" / "nwProject.nwx"
    )

# END Test testCoreProject_Backup
