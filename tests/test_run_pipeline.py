from etl import run_pipeline

ALL_STEPS = run_pipeline.DDL_FILES + run_pipeline.LOAD_FILES


def test_every_listed_sql_file_exists():
    for name in ALL_STEPS:
        assert (run_pipeline.SQL_DIR / name).is_file(), name


def test_every_sql_file_in_the_folder_is_part_of_the_pipeline():
    on_disk = {p.name for p in run_pipeline.SQL_DIR.glob("*.sql")}
    assert on_disk == set(ALL_STEPS), on_disk ^ set(ALL_STEPS)


def test_structure_is_created_in_dependency_order():
    order = run_pipeline.DDL_FILES
    assert order.index("001_schemas.sql") < order.index("002_raw_listings.sql")
    assert order.index("003_staging_listings.sql") < order.index("003b_staging_functions.sql")
    assert order.index("005_core_tables.sql") < order.index("007_history_views.sql")
    assert order.index("003_staging_listings.sql") < order.index("008_repost_candidates.sql")


def test_staging_is_loaded_before_core():
    assert run_pipeline.LOAD_FILES.index("004_load_staging.sql") < run_pipeline.LOAD_FILES.index("006_load_core.sql")