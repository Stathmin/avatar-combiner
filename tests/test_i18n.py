from i18n import TEXT


def test_languages_have_the_same_keys():
    assert set(TEXT['en']) == set(TEXT['ru'])


def test_report_labels_are_shared():
    required = {
        'sequence',
        'length',
        'gc',
        'tm',
        'hairpin',
        'homodimer',
        'heterodimer',
        'end_stability',
        'forward',
        'reverse_primer',
        'complement',
        'reverse_seq',
        'reverse_complement',
        'product',
        'wells',
        'conditions',
        'dg',
        'structure_fold',
        'delta_tm',
    }

    assert required <= set(TEXT['en'])
    assert required <= set(TEXT['ru'])
