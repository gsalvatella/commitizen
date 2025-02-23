import sys
from datetime import datetime

import pytest

from commitizen import cli, git
from commitizen.commands.changelog import Changelog
from commitizen.exceptions import (
    DryRunExit,
    NoCommitsFoundError,
    NoRevisionError,
    NotAGitProjectError,
    NotAllowed,
)
from tests.utils import create_file_and_commit, wait_for_tag


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_changelog_from_version_zero_point_two(mocker, capsys, file_regression):
    create_file_and_commit("feat: new file")
    create_file_and_commit("refactor: not in changelog")

    # create tag
    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    capsys.readouterr()

    create_file_and_commit("feat: after 0.2.0")
    create_file_and_commit("feat: after 0.2")

    testargs = ["cz", "changelog", "--start-rev", "0.2.0", "--dry-run"]
    mocker.patch.object(sys, "argv", testargs)
    with pytest.raises(DryRunExit):
        cli.main()

    out, _ = capsys.readouterr()
    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_changelog_with_different_cz(mocker, capsys, file_regression):
    create_file_and_commit("JRA-34 #comment corrected indent issue")
    create_file_and_commit("JRA-35 #time 1w 2d 4h 30m Total work logged")

    testargs = ["cz", "-n", "cz_jira", "changelog", "--dry-run"]
    mocker.patch.object(sys, "argv", testargs)

    with pytest.raises(DryRunExit):
        cli.main()
    out, _ = capsys.readouterr()
    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_changelog_from_start(mocker, capsys, changelog_path, file_regression):
    create_file_and_commit("feat: new file")
    create_file_and_commit("refactor: is in changelog")
    create_file_and_commit("Merge into master")

    testargs = ["cz", "changelog"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    with open(changelog_path, "r") as f:
        out = f.read()
    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_changelog_replacing_unreleased_using_incremental(
    mocker, capsys, changelog_path, file_regression
):
    create_file_and_commit("feat: add new output")
    create_file_and_commit("fix: output glitch")
    create_file_and_commit("Merge into master")

    testargs = ["cz", "changelog"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    create_file_and_commit("fix: mama gotta work")
    create_file_and_commit("feat: add more stuff")
    create_file_and_commit("Merge into master")

    testargs = ["cz", "changelog", "--incremental"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    with open(changelog_path, "r") as f:
        out = f.read().replace(
            datetime.strftime(datetime.now(), "%Y-%m-%d"), "2022-08-14"
        )

    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_changelog_is_persisted_using_incremental(
    mocker, capsys, changelog_path, file_regression
):

    create_file_and_commit("feat: add new output")
    create_file_and_commit("fix: output glitch")
    create_file_and_commit("Merge into master")

    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    testargs = ["cz", "changelog"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    with open(changelog_path, "a") as f:
        f.write("\nnote: this should be persisted using increment\n")

    create_file_and_commit("fix: mama gotta work")
    create_file_and_commit("feat: add more stuff")
    create_file_and_commit("Merge into master")

    testargs = ["cz", "changelog", "--incremental"]

    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    with open(changelog_path, "r") as f:
        out = f.read().replace(
            datetime.strftime(datetime.now(), "%Y-%m-%d"), "2022-08-14"
        )

    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_changelog_incremental_angular_sample(
    mocker, capsys, changelog_path, file_regression
):
    with open(changelog_path, "w") as f:
        f.write(
            "# [10.0.0-rc.3](https://github.com/angular/angular/compare/10.0.0-rc.2...10.0.0-rc.3) (2020-04-22)\n"
            "\n"
            "### Bug Fixes"
            "\n"
            "* **common:** format day-periods that cross midnight ([#36611](https://github.com/angular/angular/issues/36611)) ([c6e5fc4](https://github.com/angular/angular/commit/c6e5fc4)), closes [#36566](https://github.com/angular/angular/issues/36566)\n"
        )
    create_file_and_commit("irrelevant commit")
    git.tag("10.0.0-rc.3")

    create_file_and_commit("feat: add new output")
    create_file_and_commit("fix: output glitch")
    create_file_and_commit("fix: mama gotta work")
    create_file_and_commit("feat: add more stuff")
    create_file_and_commit("Merge into master")

    testargs = ["cz", "changelog", "--incremental"]

    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    with open(changelog_path, "r") as f:
        out = f.read()

    file_regression.check(out, extension=".md")


KEEP_A_CHANGELOG = """# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2017-06-20
### Added
- New visual identity by [@tylerfortune8](https://github.com/tylerfortune8).
- Version navigation.

### Changed
- Start using "changelog" over "change log" since it's the common usage.

### Removed
- Section about "changelog" vs "CHANGELOG".

## [0.3.0] - 2015-12-03
### Added
- RU translation from [@aishek](https://github.com/aishek).
"""


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_changelog_incremental_keep_a_changelog_sample(
    mocker, capsys, changelog_path, file_regression
):
    with open(changelog_path, "w") as f:
        f.write(KEEP_A_CHANGELOG)
    create_file_and_commit("irrelevant commit")
    git.tag("1.0.0")

    create_file_and_commit("feat: add new output")
    create_file_and_commit("fix: output glitch")
    create_file_and_commit("fix: mama gotta work")
    create_file_and_commit("feat: add more stuff")
    create_file_and_commit("Merge into master")

    testargs = ["cz", "changelog", "--incremental"]

    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    with open(changelog_path, "r") as f:
        out = f.read()

    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_changelog_hook(mocker, config):
    changelog_hook_mock = mocker.Mock()
    changelog_hook_mock.return_value = "cool changelog hook"

    create_file_and_commit("feat: new file")
    create_file_and_commit("refactor: is in changelog")
    create_file_and_commit("Merge into master")

    config.settings["change_type_order"] = ["Refactor", "Feat"]
    changelog = Changelog(
        config, {"unreleased_version": None, "incremental": True, "dry_run": False}
    )
    mocker.patch.object(changelog.cz, "changelog_hook", changelog_hook_mock)
    changelog()
    full_changelog = (
        "## Unreleased\n\n### Refactor\n\n- is in changelog\n\n### Feat\n\n- new file\n"
    )

    changelog_hook_mock.assert_called_with(full_changelog, full_changelog)


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_changelog_hook_customize(mocker, config_customize):
    changelog_hook_mock = mocker.Mock()
    changelog_hook_mock.return_value = "cool changelog hook"

    create_file_and_commit("feat: new file")
    create_file_and_commit("refactor: is in changelog")
    create_file_and_commit("Merge into master")

    changelog = Changelog(
        config_customize,
        {"unreleased_version": None, "incremental": True, "dry_run": False},
    )
    mocker.patch.object(changelog.cz, "changelog_hook", changelog_hook_mock)
    changelog()
    full_changelog = (
        "## Unreleased\n\n### Refactor\n\n- is in changelog\n\n### Feat\n\n- new file\n"
    )

    changelog_hook_mock.assert_called_with(full_changelog, full_changelog)


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_changelog_multiple_incremental_do_not_add_new_lines(
    mocker, capsys, changelog_path, file_regression
):
    """Test for bug https://github.com/commitizen-tools/commitizen/issues/192"""
    create_file_and_commit("feat: add new output")

    testargs = ["cz", "changelog", "--incremental"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    create_file_and_commit("fix: output glitch")

    testargs = ["cz", "changelog", "--incremental"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    create_file_and_commit("fix: no more explosions")

    testargs = ["cz", "changelog", "--incremental"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    create_file_and_commit("feat: add more stuff")

    testargs = ["cz", "changelog", "--incremental"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    with open(changelog_path, "r") as f:
        out = f.read()

    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_changelog_incremental_newline_separates_new_content_from_old(
    mocker, changelog_path
):
    """Test for https://github.com/commitizen-tools/commitizen/issues/509"""
    with open(changelog_path, "w") as f:
        f.write("Pre-existing content that should be kept\n")

    create_file_and_commit("feat: add more cat videos")

    testargs = ["cz", "changelog", "--incremental"]

    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    with open(changelog_path, "r") as f:
        out = f.read()

    assert (
        out
        == "Pre-existing content that should be kept\n\n## Unreleased\n\n### Feat\n\n- add more cat videos\n"
    )


def test_changelog_without_revision(mocker, tmp_commitizen_project):
    changelog_file = tmp_commitizen_project.join("CHANGELOG.md")
    changelog_file.write(
        """
        # Unreleased

        ## v1.0.0
        """
    )

    # create_file_and_commit("feat: new file")
    testargs = ["cz", "changelog", "--incremental"]
    mocker.patch.object(sys, "argv", testargs)

    with pytest.raises(NoRevisionError):
        cli.main()


def test_changelog_incremental_with_revision(mocker):
    """combining incremental with a revision doesn't make sense"""
    testargs = ["cz", "changelog", "--incremental", "0.2.0"]
    mocker.patch.object(sys, "argv", testargs)

    with pytest.raises(NotAllowed):
        cli.main()


def test_changelog_with_different_tag_name_and_changelog_content(
    mocker, tmp_commitizen_project
):
    changelog_file = tmp_commitizen_project.join("CHANGELOG.md")
    changelog_file.write(
        """
        # Unreleased

        ## v1.0.0
        """
    )
    create_file_and_commit("feat: new file")
    git.tag("2.0.0")

    # create_file_and_commit("feat: new file")
    testargs = ["cz", "changelog", "--incremental"]
    mocker.patch.object(sys, "argv", testargs)

    with pytest.raises(NoRevisionError):
        cli.main()


def test_changelog_in_non_git_project(tmpdir, config, mocker):
    testargs = ["cz", "changelog", "--incremental"]
    mocker.patch.object(sys, "argv", testargs)

    with tmpdir.as_cwd():
        with pytest.raises(NotAGitProjectError):
            cli.main()


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_breaking_change_content_v1_beta(mocker, capsys, file_regression):
    commit_message = (
        "feat(users): email pattern corrected\n\n"
        "BREAKING CHANGE: migrate by renaming user to users\n\n"
        "footer content"
    )
    create_file_and_commit(commit_message)
    testargs = ["cz", "changelog", "--dry-run"]
    mocker.patch.object(sys, "argv", testargs)
    with pytest.raises(DryRunExit):
        cli.main()
    out, _ = capsys.readouterr()
    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_breaking_change_content_v1(mocker, capsys, file_regression):
    commit_message = (
        "feat(users): email pattern corrected\n\n"
        "body content\n\n"
        "BREAKING CHANGE: migrate by renaming user to users"
    )
    create_file_and_commit(commit_message)
    testargs = ["cz", "changelog", "--dry-run"]
    mocker.patch.object(sys, "argv", testargs)
    with pytest.raises(DryRunExit):
        cli.main()
    out, _ = capsys.readouterr()

    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_breaking_change_content_v1_multiline(mocker, capsys, file_regression):
    commit_message = (
        "feat(users): email pattern corrected\n\n"
        "body content\n\n"
        "BREAKING CHANGE: migrate by renaming user to users.\n"
        "and then connect the thingy with the other thingy\n\n"
        "footer content"
    )
    create_file_and_commit(commit_message)
    testargs = ["cz", "changelog", "--dry-run"]
    mocker.patch.object(sys, "argv", testargs)
    with pytest.raises(DryRunExit):
        cli.main()
    out, _ = capsys.readouterr()
    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_changelog_config_flag_increment(
    mocker, changelog_path, config_path, file_regression
):

    with open(config_path, "a") as f:
        f.write("changelog_incremental = true\n")
    with open(changelog_path, "a") as f:
        f.write("\nnote: this should be persisted using increment\n")

    create_file_and_commit("feat: add new output")

    testargs = ["cz", "changelog"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    with open(changelog_path, "r") as f:
        out = f.read()

    assert "this should be persisted using increment" in out
    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_changelog_config_start_rev_option(
    mocker, capsys, config_path, file_regression
):

    # create commit and tag
    create_file_and_commit("feat: new file")
    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    capsys.readouterr()

    create_file_and_commit("feat: after 0.2.0")
    create_file_and_commit("feat: after 0.2")

    with open(config_path, "a") as f:
        f.write('changelog_start_rev = "0.2.0"\n')

    testargs = ["cz", "changelog", "--dry-run"]
    mocker.patch.object(sys, "argv", testargs)
    with pytest.raises(DryRunExit):
        cli.main()

    out, _ = capsys.readouterr()
    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_changelog_incremental_keep_a_changelog_sample_with_annotated_tag(
    mocker, capsys, changelog_path, file_regression
):
    """Fix #378"""
    with open(changelog_path, "w") as f:
        f.write(KEEP_A_CHANGELOG)
    create_file_and_commit("irrelevant commit")
    git.tag("1.0.0", annotated=True)

    create_file_and_commit("feat: add new output")
    create_file_and_commit("fix: output glitch")
    create_file_and_commit("fix: mama gotta work")
    create_file_and_commit("feat: add more stuff")
    create_file_and_commit("Merge into master")

    testargs = ["cz", "changelog", "--incremental"]

    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    with open(changelog_path, "r") as f:
        out = f.read()

    file_regression.check(out, extension=".md")


@pytest.mark.parametrize("test_input", ["rc", "alpha", "beta"])
@pytest.mark.usefixtures("tmp_commitizen_project")
@pytest.mark.freeze_time("2021-06-11")
def test_changelog_incremental_with_release_candidate_version(
    mocker, changelog_path, file_regression, test_input
):
    """Fix #357"""
    with open(changelog_path, "w") as f:
        f.write(KEEP_A_CHANGELOG)
    create_file_and_commit("irrelevant commit")
    git.tag("1.0.0", annotated=True)

    create_file_and_commit("feat: add new output")
    create_file_and_commit("fix: output glitch")

    testargs = ["cz", "bump", "--changelog", "--prerelease", test_input, "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    create_file_and_commit("fix: mama gotta work")
    create_file_and_commit("feat: add more stuff")
    create_file_and_commit("Merge into master")

    testargs = ["cz", "changelog", "--incremental"]

    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    with open(changelog_path, "r") as f:
        out = f.read()

    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_changelog_with_filename_as_empty_string(mocker, changelog_path, config_path):

    with open(config_path, "a") as f:
        f.write("changelog_file = true\n")

    create_file_and_commit("feat: add new output")

    testargs = ["cz", "changelog"]
    mocker.patch.object(sys, "argv", testargs)
    with pytest.raises(NotAllowed):
        cli.main()


@pytest.mark.usefixtures("tmp_commitizen_project")
@pytest.mark.freeze_time("2022-02-13")
def test_changelog_from_rev_first_version_from_arg(
    mocker, config_path, changelog_path, file_regression
):
    mocker.patch("commitizen.git.GitTag.date", "2022-02-13")

    with open(config_path, "a") as f:
        f.write('tag_format = "$version"\n')

    # create commit and tag
    create_file_and_commit("feat: new file")

    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    wait_for_tag()

    create_file_and_commit("feat: after 0.2.0")
    create_file_and_commit("feat: another feature")

    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    testargs = ["cz", "changelog", "0.2.0"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    with open(changelog_path, "r") as f:
        out = f.read()

    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
@pytest.mark.freeze_time("2022-02-13")
def test_changelog_from_rev_latest_version_from_arg(
    mocker, config_path, changelog_path, file_regression
):
    mocker.patch("commitizen.git.GitTag.date", "2022-02-13")

    with open(config_path, "a") as f:
        f.write('tag_format = "$version"\n')

    # create commit and tag
    create_file_and_commit("feat: new file")
    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    wait_for_tag()

    create_file_and_commit("feat: after 0.2.0")
    create_file_and_commit("feat: another feature")

    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    wait_for_tag()

    testargs = ["cz", "changelog", "0.3.0"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    with open(changelog_path, "r") as f:
        out = f.read()

    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
@pytest.mark.freeze_time("2022-02-13")
def test_changelog_from_rev_single_version_not_found(
    mocker, config_path, changelog_path
):
    """Provides an invalid revision ID to changelog command"""
    with open(config_path, "a") as f:
        f.write('tag_format = "$version"\n')

    # create commit and tag
    create_file_and_commit("feat: new file")
    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    wait_for_tag()

    create_file_and_commit("feat: after 0.2.0")
    create_file_and_commit("feat: another feature")

    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    wait_for_tag()

    testargs = ["cz", "changelog", "0.8.0"]  # it shouldn't exist
    mocker.patch.object(sys, "argv", testargs)
    with pytest.raises(NoCommitsFoundError) as excinfo:
        cli.main()

    assert "Could not find a valid revision" in str(excinfo)


@pytest.mark.usefixtures("tmp_commitizen_project")
@pytest.mark.freeze_time("2022-02-13")
def test_changelog_from_rev_range_version_not_found(mocker, config_path):
    """Provides an invalid end revision ID to changelog command"""
    with open(config_path, "a") as f:
        f.write('tag_format = "$version"\n')

    # create commit and tag
    create_file_and_commit("feat: new file")
    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    create_file_and_commit("feat: after 0.2.0")
    create_file_and_commit("feat: another feature")

    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    testargs = ["cz", "changelog", "0.5.0..0.8.0"]  # it shouldn't exist
    mocker.patch.object(sys, "argv", testargs)
    with pytest.raises(NoCommitsFoundError) as excinfo:
        cli.main()

    assert "Could not find a valid revision" in str(excinfo)


@pytest.mark.usefixtures("tmp_commitizen_project")
@pytest.mark.freeze_time("2022-02-13")
def test_changelog_from_rev_version_range_including_first_tag(
    mocker, config_path, changelog_path, file_regression
):
    mocker.patch("commitizen.git.GitTag.date", "2022-02-13")

    with open(config_path, "a") as f:
        f.write('tag_format = "$version"\n')

    # create commit and tag
    create_file_and_commit("feat: new file")
    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    create_file_and_commit("feat: after 0.2.0")
    create_file_and_commit("feat: another feature")

    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()

    testargs = ["cz", "changelog", "0.2.0..0.3.0"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    with open(changelog_path, "r") as f:
        out = f.read()

    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
@pytest.mark.freeze_time("2022-02-13")
def test_changelog_from_rev_version_range_from_arg(
    mocker, config_path, changelog_path, file_regression
):
    mocker.patch("commitizen.git.GitTag.date", "2022-02-13")

    with open(config_path, "a") as f:
        f.write('tag_format = "$version"\n')

    # create commit and tag
    create_file_and_commit("feat: new file")
    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    wait_for_tag()
    create_file_and_commit("feat: after 0.2.0")
    create_file_and_commit("feat: another feature")

    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    wait_for_tag()

    create_file_and_commit("feat: getting ready for this")

    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    wait_for_tag()

    testargs = ["cz", "changelog", "0.3.0..0.4.0"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    with open(changelog_path, "r") as f:
        out = f.read()

    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
@pytest.mark.freeze_time("2022-02-13")
def test_changelog_from_rev_version_with_big_range_from_arg(
    mocker, config_path, changelog_path, file_regression
):
    mocker.patch("commitizen.git.GitTag.date", "2022-02-13")

    with open(config_path, "a") as f:
        f.write('tag_format = "$version"\n')

    # create commit and tag
    create_file_and_commit("feat: new file")

    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    wait_for_tag()

    create_file_and_commit("feat: after 0.2.0")
    create_file_and_commit("feat: another feature")

    testargs = ["cz", "bump", "--yes"]  # 0.3.0
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    wait_for_tag()
    create_file_and_commit("feat: getting ready for this")

    testargs = ["cz", "bump", "--yes"]  # 0.4.0
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    wait_for_tag()
    create_file_and_commit("fix: small error")

    testargs = ["cz", "bump", "--yes"]  # 0.4.1
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    wait_for_tag()
    create_file_and_commit("feat: new shinny feature")

    testargs = ["cz", "bump", "--yes"]  # 0.5.0
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    wait_for_tag()
    create_file_and_commit("feat: amazing different shinny feature")
    # dirty hack to avoid same time between tags

    testargs = ["cz", "bump", "--yes"]  # 0.6.0
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    wait_for_tag()

    testargs = ["cz", "changelog", "0.3.0..0.5.0"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    with open(changelog_path, "r") as f:
        out = f.read()

    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
@pytest.mark.freeze_time("2022-02-13")
def test_changelog_from_rev_latest_version_dry_run(
    mocker, capsys, config_path, changelog_path, file_regression
):
    mocker.patch("commitizen.git.GitTag.date", "2022-02-13")

    with open(config_path, "a") as f:
        f.write('tag_format = "$version"\n')

    # create commit and tag
    create_file_and_commit("feat: new file")
    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    wait_for_tag()

    create_file_and_commit("feat: after 0.2.0")
    create_file_and_commit("feat: another feature")

    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    capsys.readouterr()
    wait_for_tag()

    testargs = ["cz", "changelog", "0.3.0", "--dry-run"]
    mocker.patch.object(sys, "argv", testargs)
    with pytest.raises(DryRunExit):
        cli.main()

    out, _ = capsys.readouterr()

    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_invalid_subject_is_skipped(mocker, capsys):
    """Fix #510"""
    non_conformant_commit_title = (
        "Merge pull request #487 from manang/master\n\n"
        "feat: skip merge messages that start with Pull request\n"
    )
    create_file_and_commit(non_conformant_commit_title)
    create_file_and_commit("feat: a new world")
    testargs = ["cz", "changelog", "--dry-run"]
    mocker.patch.object(sys, "argv", testargs)
    with pytest.raises(DryRunExit):
        cli.main()
    out, _ = capsys.readouterr()

    assert out == ("## Unreleased\n\n### Feat\n\n- a new world\n\n")


@pytest.mark.freeze_time("2022-02-13")
@pytest.mark.usefixtures("tmp_commitizen_project")
def test_changelog_with_customized_change_type_order(
    mocker, config_path, changelog_path, file_regression
):
    mocker.patch("commitizen.git.GitTag.date", "2022-02-13")

    with open(config_path, "a") as f:
        f.write('tag_format = "$version"\n')
        f.write(
            'change_type_order = ["BREAKING CHANGE", "Perf", "Fix", "Feat", "Refactor"]\n'
        )

    # create commit and tag
    create_file_and_commit("feat: new file")
    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    wait_for_tag()
    create_file_and_commit("feat: after 0.2.0")
    create_file_and_commit("feat: another feature")
    create_file_and_commit("fix: fix bug")

    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    wait_for_tag()

    create_file_and_commit("feat: getting ready for this")
    create_file_and_commit("perf: perf improvement")

    testargs = ["cz", "bump", "--yes"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    wait_for_tag()

    testargs = ["cz", "changelog", "0.3.0..0.4.0"]
    mocker.patch.object(sys, "argv", testargs)
    cli.main()
    with open(changelog_path, "r") as f:
        out = f.read()

    file_regression.check(out, extension=".md")


@pytest.mark.usefixtures("tmp_commitizen_project")
def test_empty_commit_list(mocker):
    create_file_and_commit("feat: a new world")

    # test changelog properly handles when no commits are found for the revision
    mocker.patch("commitizen.git.get_commits", return_value=[])
    testargs = ["cz", "changelog"]
    mocker.patch.object(sys, "argv", testargs)
    with pytest.raises(NoCommitsFoundError):
        cli.main()
