Python API
==========

Build a report from a layout file::

    from tuttireporting import build_project

    build_project("report", "run/manifest.toml", report_path="report.toml")

Or use a catalog definition::

    build_project("report", "run/manifest.toml", catalog_name="biso")

.. automodule:: tuttireporting.builder
   :members: build_project, compile_project, zip_project

.. automodule:: tuttireporting.catalog
   :members: list_reports, report_path, export_report

.. automodule:: tuttireporting.manifest
   :members: load_report
