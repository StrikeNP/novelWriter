"""
novelWriter – Spell Check Classes Tester
========================================

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

import sys
import pytest
import enchant

from pathlib import Path

from tools import buildTestProject
from mocked import causeOSError

from novelwriter.constants import nwFiles
from novelwriter.core.project import NWProject
from novelwriter.core.spellcheck import FakeEnchant, NWSpellEnchant, UserDictionary


@pytest.mark.core
def testCoreSpell_UserDictionary(monkeypatch, mockGUI, fncPath):
    """Test the UserDictionary class."""
    project = NWProject()
    buildTestProject(project, fncPath)

    # Check that there is no file before we start
    dictFile = project.storage.getMetaFile(nwFiles.DICT_FILE)
    assert isinstance(dictFile, Path)
    assert not dictFile.exists()

    # Add a couple of words
    userDict = UserDictionary(project)
    assert userDict.add("foo") is True
    assert userDict.add("bar") is True
    assert userDict.add("bar") is False  # No duplicates

    # Check that we have them
    assert "foo" in userDict
    assert "bar" in userDict

    # Check the iterator
    assert sorted(userDict) == ["bar", "foo"]

    # Save the file, but fail
    with monkeypatch.context() as mp:
        mp.setattr("builtins.open", causeOSError)
        userDict.save()

    # There should be no file
    assert not dictFile.exists()

    # Break the path check
    with monkeypatch.context() as mp:
        mp.setattr("novelwriter.core.storage.NWStorage.getMetaFile", lambda *a: None)
        userDict.save()

    # There should still be no file
    assert not dictFile.exists()

    # Save proper
    userDict.save()
    assert dictFile.exists()

    # Clear the dictionary
    userDict._words = set()
    assert sorted(userDict) == []

    # Load the file, but fail
    with monkeypatch.context() as mp:
        mp.setattr("builtins.open", causeOSError)
        userDict.load()

    # No words loaded
    assert sorted(userDict) == []

    # Break the path check
    with monkeypatch.context() as mp:
        mp.setattr("novelwriter.core.storage.NWStorage.getMetaFile", lambda *a: None)
        userDict.load()

    # No words loaded
    assert sorted(userDict) == []

    # Load the words again, properly
    userDict.load()
    assert sorted(userDict) == ["bar", "foo"]

# END Test testCoreSpell_UserDictionary


@pytest.mark.core
def testCoreSpell_FakeEnchant(monkeypatch, mockGUI, fncPath):
    """Test the FakeEnchant spell checker fallback."""
    project = NWProject()
    buildTestProject(project, fncPath)

    # Make package import fail
    with monkeypatch.context() as mp:
        mp.setitem(sys.modules, "enchant", None)
        spChk = NWSpellEnchant(project)
        spChk.setLanguage("en_US")
        assert isinstance(spChk._enchant, FakeEnchant)

    # Request a non-existent dictionary
    spChk = NWSpellEnchant(project)
    spChk.setLanguage("whatchamajig")
    assert isinstance(spChk._enchant, FakeEnchant)

    # Request an empty language string
    # See issue https://github.com/vkbo/novelWriter/issues/1096
    spChk = NWSpellEnchant(project)
    spChk.setLanguage("")
    assert isinstance(spChk._enchant, FakeEnchant)

    # FakeEnchant should handle requests
    fkChk = FakeEnchant()
    assert fkChk.tag == ""
    assert fkChk.provider.name == ""
    assert fkChk.check("whatchamajig") is True
    assert fkChk.suggest("whatchamajig") == []
    assert fkChk.add_to_session("whatchamajig") is None

# END Test testCoreSpell_FakeEnchant


@pytest.mark.core
def testCoreSpell_Enchant(monkeypatch, mockGUI, fncPath):
    """Test the pyenchant spell checker."""
    project = NWProject()
    buildTestProject(project, fncPath)

    # Break the enchant package, and check error handling
    with monkeypatch.context() as mp:
        mp.setitem(sys.modules, "enchant", None)
        spChk = NWSpellEnchant(project)
        assert spChk.spellLanguage is None
        assert spChk.listDictionaries() == []
        assert spChk.describeDict() == ("", "")

        spChk.setLanguage("en_US")
        assert spChk.spellLanguage is None

        # Check that the FakeEnchant class is actually handling this
        assert isinstance(spChk._enchant, FakeEnchant)
        assert spChk.checkWord("word") is True
        assert spChk.suggestWords("word") == []
        assert spChk.addWord("word") is True

    # Set the dict to None, and check enchant error handling
    spChk = NWSpellEnchant(project)
    spChk._enchant = None  # type: ignore
    assert spChk.checkWord("word") is True
    assert spChk.suggestWords("word") == []
    assert spChk.addWord("word") is False
    assert spChk.addWord("\n\t ") is False
    assert spChk.describeDict() == ("", "")

    # Load the proper enchant package (twice)
    spChk = NWSpellEnchant(project)
    spChk.setLanguage("en_US")
    spChk.setLanguage("en_US")
    assert isinstance(spChk._enchant, enchant.Dict)
    assert spChk.spellLanguage == "en_US"
    assert spChk.listDictionaries() != []
    assert spChk.describeDict() != ("", "")

    # Set to non-existent language
    spChk.setLanguage("foo_bar")

    # Block the broker from figuring out the language
    with monkeypatch.context() as mp:
        mp.setattr("enchant.Broker.request_dict", lambda *a: None)
        spChk.setLanguage("en_US")
        assert isinstance(spChk._enchant, FakeEnchant)

# END Test testCoreSpell_Enchant
