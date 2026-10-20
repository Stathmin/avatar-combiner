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

    await user.should_see('Avatar Combiner')
    await user.should_see('plates.xlsx')


async def test_tools_page_lists_tools(user: User):
    await user.open('/tools')

    await user.should_see('Primer Tm')
    await user.should_see('Structure')
    await user.should_see('PCR')


async def test_run_from_web(user: User):
    await user.open('/')
    await user.should_see('Run')

    user.find('Run').click()

    await user.should_see('Done:', retries=50)
