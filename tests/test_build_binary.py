import build_binary


def test_collects_reachable_local_modules():
    modules = set(build_binary.collect_local_modules())

    assert {
        'app_config',
        'combine_plates',
        'extract_plates_from_excel',
        'pcr_tools',
        'plate_layout',
        'report_xlsx',
        'seq_import',
        'seq_structure',
        'tools',
        'ui',
        'web_app',
    } <= modules


def test_skips_build_and_standalone_scripts():
    modules = set(build_binary.collect_local_modules())

    assert 'build_binary' not in modules
    assert 'fix_cultivar_names' not in modules
    assert 'generate_test_plates' not in modules
