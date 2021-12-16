{
    "name": "PMS Guesty Connector",
    "author": "Casai (jorge.juarez@casai.com)",
    "website": "https://github.com/casai-org/pms",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "depends": [
        "base",
        "pms_base",
        "pms_sale",
        "queue_job"
    ],
    "data": [
        "views/backend_guesty.xml",
        "views/pms_property.xml",
        "views/pms_reservation.xml",
        "security/ir.model.access.csv"
    ],
    "installable": True
}
