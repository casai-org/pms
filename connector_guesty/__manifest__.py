{
    "name": "PMS Guesty Connector",
    "author": "Casai (jorge.juarez@casai.com)",
    "website": "https://github.com/casai-org/pms",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "depends": [
        "base",
        "pms",
        "queue_job"
    ],
    "data": [
        "views/backend_guesty.xml"
    ],
    "installable": True,
    "external_dependencies": ["odoo14-addon-queue-job"]
}
