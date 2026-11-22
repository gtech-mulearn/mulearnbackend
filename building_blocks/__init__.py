"""Technical capabilities every module may use: ids, the clock, errors, logging, commands.

building_blocks holds no business rules and imports no module and no legacy package
(api, db, utils, mu_celery). .importlinter enforces both. See docs/architecture/04-module-rules.md.
"""
