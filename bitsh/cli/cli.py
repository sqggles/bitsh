"""Define the top-level cli command."""
import os

import click
from pbr import version

import pandas as pd
import sqlalchemy as sa
import blaze as bz
import odo
import logging

from bitsh.cli.base import AbstractCommand
from bitsh import log
from bitsh import config


logger = log.getLogger(__name__)

# Retrieve the project version from PBR.
try:
    version_info = version.VersionInfo('processor-cli')
    __version__ = version_info.release_string()
except AttributeError:
    __version__ = None

APP_NAME = 'bitsh'

@click.group()
@click.version_option(version=__version__)
@click.option(
    '--log-level',
    '-l',
    default='NOTSET',
    type=click.Choice(['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
    help='defines the log level',
    show_default=True)
@click.pass_context
def cli(ctx, log_level):
    """Manage CLI commands."""
    ctx.obj = {**ctx.params}
    ctx.auto_envvar_prefix = 'COM'

    # Load defaults from configuration file if any.
    cfg_path = os.path.join(click.get_app_dir(APP_NAME), APP_NAME+'.conf')
    cfg = cfg_path if os.path.exists(cfg_path) else None
    ctx.default_map = config.load(cfg, with_defaults=True, validate=True)


@click.command()
def hello_world():
    """Greet the world."""
    click.echo('Hello World!')


@click.option('-d','--dburl', help='sqlalchemy url for the database')
@click.option('-s','--schema', default=None, help='schema to use')
@click.option('-t','--tblname', help='table name to dump')
@click.option('-p','--parquet', help='output as parquet files',
              type=click.BOOL, is_flag=True, default=False)
@click.option('-q','--sqlite', help='output as an sqlite3 db',
              type=click.BOOL, is_flag=True, default=False)
@click.option('-f','--feather', help='output as feather files',
              type=click.BOOL, is_flag=True, default=False)
@click.option('--csv', help='output as csv files',
              type=click.BOOL, is_flag=True, default=False)
@click.option('--tsv', help='output as tsv files',
              type=click.BOOL, is_flag=True, default=False)
@click.command()
def dumpdb(dburl, schema, tblname, parquet, sqlite, feather, csv, tsv):
    md = sa.MetaData(dburl, schema=schema)
    db = bz.data(md)
    odbname = schema if schema else dburl.split('/')[-1]
    if odbname == '' or odbname is None:
        odbname = 'dump'
    if not os.path.exists(odbname):
        os.makedirs(odbname)
    for tbl in db.data.tables.keys():
        if sqlite:
            sadburl = 'sqlite://%s.sqlite3.db::%s' % (odbname, tblname)
            odo(tbl, sadburl)
        if csv:
            odo(tbl, '%s/%s.csv')
        if tsv:
            odo(tbl, '%s/%s.tsv')
        if parquet or feather:
            df = odo(tbl, pd.DataFrame)
            if parquet:
                df.to_parquet('%s/%s.parquet' % (odbname, tblname))
            if feather:
                import feather as ft
                feather.write_dataframe('%s/%s.feather' % (odbname, tblname))


cli.add_command(hello_world)
cli.add_command(dumpdb)
