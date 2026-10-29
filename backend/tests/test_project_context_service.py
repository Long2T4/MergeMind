"""Project context selection uses supplied text only, with no database or AI."""

import pytest

from app.services.project_context_service import collect_project_context


def paths(result):
    return [file.path for file in result.files]


def test_python_import_selects_related_module_and_preserves_contents():
    files = {"models.py": "class User: pass\n", "unrelated.py": "secret = 1"}
    result = collect_project_context("main.py", "from models import User", files)
    assert paths(result) == ["models.py"]
    assert result.files[0].content == files["models.py"]
    assert result.unresolved_imports == ()
    assert result.total_chars == len(files["models.py"])


def test_python_absolute_imports_use_configured_source_root():
    result = collect_project_context(
        "backend/app/routes/review.py",
        "from app.models.models import User\nimport app.services.context as context",
        {
            "backend/app/models/models.py": "class User: pass",
            "backend/app/services/context.py": "def collect(): pass",
            "app/models/models.py": "wrong import root",
        },
        source_root="backend",
    )
    assert paths(result) == ["backend/app/models/models.py", "backend/app/services/context.py"]


def test_python_relative_imports_and_packages():
    result = collect_project_context(
        "app/routes/review.py",
        "from ..models import User\nfrom . import helpers\nimport app.settings",
        {
            "app/models/__init__.py": "class User: pass",
            "app/routes/helpers.py": "def help_review(): pass",
            "app/settings/__init__.py": "DEBUG = False",
        },
    )
    assert paths(result) == [
        "app/models/__init__.py", "app/routes/helpers.py", "app/settings/__init__.py",
    ]


def test_from_package_resolves_multiple_submodules_and_star_import():
    result = collect_project_context(
        "main.py", "from app import models, routes\nfrom settings import *",
        {"app/models.py": "models", "app/routes.py": "routes", "settings.py": "settings"},
    )
    assert paths(result) == ["app/models.py", "app/routes.py", "settings.py"]


def test_missing_and_external_python_imports_are_diagnostics():
    result = collect_project_context(
        "main.py", "import missing\nimport missing\nimport requests\nimport models",
        {"models.py": "class User: pass"},
    )
    assert paths(result) == ["models.py"]
    assert result.unresolved_imports == ("missing", "requests")


def test_incomplete_python_is_not_guessed_and_never_executed():
    incomplete = collect_project_context("main.py", "from models import (", {"models.py": "model"})
    assert incomplete.files == ()
    result = collect_project_context(
        "main.py", "raise RuntimeError('do not execute')\nimport models",
        {"models.py": "raise RuntimeError('do not execute dependency')"},
    )
    assert paths(result) == ["models.py"]


def test_python_comments_strings_and_dynamic_imports_are_not_dependencies():
    result = collect_project_context(
        "main.py", '# import models\nexample = "import models"\n__import__("models")',
        {"models.py": "model"},
    )
    assert result.files == ()


@pytest.mark.parametrize("extension", ["js", "jsx", "ts", "tsx", "mjs", "cjs"])
def test_js_static_imports_reexports_side_effects_and_require(extension):
    result = collect_project_context(
        f"src/main.{extension}",
        '''import {User} from './models.js'
        import './setup.js';
        export {validate} from '../validation.js';
        const api = require('./api.js');''',
        {
            "src/models.js": "export class User {}",
            "src/setup.js": "initialize()",
            "validation.js": "export function validate() {}",
            "src/api.js": "module.exports = {}",
            "src/unrelated.js": "unrelated",
        },
    )
    assert paths(result) == ["src/models.js", "src/setup.js", "validation.js", "src/api.js"]


def test_typescript_multiline_import_and_directory_index():
    result = collect_project_context(
        "src/main.ts", "import type {\n User,\n Role\n} from './models'\nimport * as api from './api'",
        {"src/models.ts": "export type User = {}", "src/models.js": "wrong", "src/api/index.ts": "api"},
    )
    assert paths(result) == ["src/models.ts", "src/api/index.ts"]


def test_js_ignores_comments_strings_templates_external_and_dynamic_imports():
    result = collect_project_context(
        "main.js",
        '''// import './fake.js';
        /* const fake = require('./fake.js'); */
        const example = "import './fake.js'";
        const template = `import './fake.js'`;
        import React from 'react';
        import alias from '@/models';
        import('./fake.js');
        loader.require('./fake.js');
        ''',
        {"fake.js": "fake"},
    )
    assert result.files == ()
    assert result.unresolved_imports == ()


def test_js_unresolved_import_does_not_block_valid_context():
    result = collect_project_context(
        "src/main.js", "import './missing'; import './models.js'",
        {"src/models.js": "models"},
    )
    assert paths(result) == ["src/models.js"]
    assert result.unresolved_imports == ("./missing",)


def test_js_cannot_resolve_above_project_root_or_include_non_code_files():
    result = collect_project_context(
        "src/main.js", "import '../../outside'; import '../.env'",
        {"outside.js": "outside", ".env": "PRIVATE=example"},
    )
    assert result.files == ()
    assert result.unresolved_imports == ("../../outside", "../.env")


def test_relative_python_import_cannot_escape_source_root():
    result = collect_project_context(
        "backend/app/main.py", "from ...outside import value",
        {"outside.py": "outside"}, source_root="backend",
    )
    assert result.files == ()
    assert result.unresolved_imports == ("...outside",)


def test_deduplicates_dependencies_and_excludes_reviewed_file():
    result = collect_project_context(
        "main.py", "import models\nfrom models import User\nimport main",
        {"main.py": "old submitted code", "models.py": "model"},
    )
    assert paths(result) == ["models.py"]
    assert result.omitted_files == ()


def test_collects_direct_dependencies_only():
    result = collect_project_context(
        "main.py", "import models", {"models.py": "import settings", "settings.py": "settings"},
    )
    assert paths(result) == ["models.py"]


def test_file_budget_follows_import_order_independent_of_mapping_order():
    result = collect_project_context(
        "main.py", "import first\nimport second",
        {"second.py": "2", "first.py": "1"}, max_files=1,
    )
    assert paths(result) == ["first.py"]
    assert result.omitted_files == ("second.py",)


def test_character_budget_skips_whole_large_files_and_continues():
    result = collect_project_context(
        "main.py", "import large\nimport small\nimport extra",
        {"large.py": "x" * 11, "small.py": "x" * 10, "extra.py": "x"}, max_chars=10,
    )
    assert paths(result) == ["small.py"]
    assert result.total_chars == 10
    assert result.omitted_files == ("large.py", "extra.py")


def test_budget_counts_unicode_characters_and_accepts_empty_files():
    result = collect_project_context(
        "main.py", "import empty\nimport unicode",
        {"empty.py": "", "unicode.py": "é日"}, max_chars=2,
    )
    assert paths(result) == ["empty.py", "unicode.py"]
    assert result.total_chars == 2


def test_normalizes_windows_separators_without_mutating_input():
    files = {"src\\models.py": "model"}
    result = collect_project_context("src\\main.py", "from . import models", files)
    assert paths(result) == ["src/models.py"]
    assert files == {"src\\models.py": "model"}


@pytest.mark.parametrize("path", ["/tmp/main.py", "../main.py", "a/../main.py", "C:\\main.py", "", ".", "a\x00.py"])
def test_rejects_invalid_reviewed_paths(path):
    with pytest.raises(ValueError):
        collect_project_context(path, "", {})


@pytest.mark.parametrize("path", ["/tmp/models.py", "../models.py", "C:\\models.py"])
def test_rejects_invalid_supplied_paths(path):
    with pytest.raises(ValueError):
        collect_project_context("main.py", "", {path: "content"})


@pytest.mark.parametrize("value", [0, -1, 1.5, True, "8"])
@pytest.mark.parametrize("name", ["max_files", "max_chars"])
def test_rejects_invalid_limits(name, value):
    with pytest.raises(ValueError):
        collect_project_context("main.py", "", {}, **{name: value})


def test_rejects_duplicate_normalized_paths_non_text_and_wrong_source_root():
    with pytest.raises(ValueError, match="Duplicate"):
        collect_project_context("main.py", "", {"./models.py": "1", "models.py": "2"})
    with pytest.raises(ValueError, match="contents"):
        collect_project_context("main.py", "", {"models.py": b"binary"})
    with pytest.raises(ValueError, match="Source code"):
        collect_project_context("main.py", None, {})
    with pytest.raises(ValueError, match="source_root"):
        collect_project_context("frontend/main.py", "", {}, source_root="backend")
    with pytest.raises(ValueError, match="Supported"):
        collect_project_context("main.java", "", {})
