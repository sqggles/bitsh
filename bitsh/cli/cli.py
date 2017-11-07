"""Define the top-level cli command."""
import os
import json
import click
from pbr import version

import pandas as pd
import sqlalchemy as sa
import blaze as bz
from odo import odo
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


@click.option('-u','--dburl', envvar='DATABASE_URL',
              help='sqlalchemy url for the database')
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
    dburl = sa.engine.url.make_url(dburl)
    passwd = os.environ.get('DB_PASSWORD', False)
    if passwd:
        dburl.password = passwd
    logger.info(
        'connecting to {host:"%s", port:%s, db:"%s", schema:"%s", table: "%s", driver:"%s"}' % 
        (dburl.host, dburl.port, dburl.database, schema, tblname, dburl.drivername))
    md = sa.MetaData(dburl, schema=schema)
    db = bz.data(md)
    odbname = schema if schema is not None else dburl.database
    if not os.path.exists(odbname):
        os.makedirs(odbname)
    otbls = list(db.data.tables.keys())
    logger.info('found the following tables in db: ' + str(otbls))
    ngin = None
    if not (sqlite or csv or tsv or parquet or feather):
        sqlite = True
    if sqlite:
        sadburl = 'sqlite:///%s.sqlite3.db' % odbname
        ngin = sa.create_engine(sadburl)
    if tblname:
        otbls = [tblname]
    for tbln in otbls:
        if tbln.startswith(schema):
            tbln = tbln.split('.')[1]
        tbl = db[tbln]
        logger.info('processing {table:%s, rows:%d,  schema:%s' % (tbln, tbl.nrows, tbl.schema))
        ofpfx = '%s/%s.' % (odbname, tbln)
        df = odo(tbl, pd.DataFrame)
        if sqlite:
             df.to_sql(tbln, ngin)
        if csv:
            odo(tbl, '%s.csv' % (ofpfx))
        if tsv:
            odo(tbl, '%s.tsv' % (ofpfx))
        if parquet:
            import pyarrow as pa
            import pyarrow.parquet as pq
            table = pa.Table.from_pandas(df)
            pq.write_table(table, '%s.parquet' % ofpfx)
        if feather:
            import pyarrow as pa
            import pyarrow.feather as pf

            pf.write_feather(df, '%s.feather' % (ofpfx))


cli.add_command(hello_world)
cli.add_command(dumpdb)
