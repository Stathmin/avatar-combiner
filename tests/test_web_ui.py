import os
import shutil
import tempfile
from pathlib import Path

import pytest
from nicegui.testing import User

pytest_plugins = ['nicegui.testing.user_plugin']

WORKBOOK = Path(__file__).resolve().parents[1] / 'src' / 'планшеты соя пробелы.xlsx'

BASE = Path(tempfile.mkdtemp(prefix='avatar-web-'))
shutil.copy(WORKBOOK, BASE / 'plates.xlsx')
os.environ['AVATAR_WEB_BASE'] = str(BASE)

pytestmark = pytest.mark.nicegui_main_file('tests/web_main.py')


async def test_home_shows_workbook(user: User):
    await user.open('/')

    await user.should_see('AVATAR COMBINER')
    await user.should_see('plates.xlsx')


async def test_nav_lists_every_tool(user: User):
    await user.open('/')

    for name in (
        'Pipeline',
        'Results',
        'Primer Tm',
        'Primer pair',
        'DNA',
        'Units',
        'Structure',
        'PCR',
        'Import sequence',
        'Plate layout',
        'XLSX export',
    ):
        await user.should_see(name)


async def test_tools_page_lists_tools(user: User):
    await user.open('/tools')

    for name in (
        'Primer Tm',
        'Primer pair',
        'DNA',
        'Units',
        'Structure',
        'PCR',
        'Import',
        'Layout',
        'XLSX',
    ):
        await user.should_see(name)


async def test_tool_query_selects_tab(user: User):
    await user.open('/tools?tool=pcr')

    await user.should_see('Simulate')


async def test_run_from_web(user: User):
    await user.open('/')
    await user.should_see('Run')

    user.find('Run').click()

    await user.should_see('Done:', retries=50)
