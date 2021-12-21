{
    "name": "PMS Guesty Connector",
    "author": "Casai, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/pms",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "depends": ["base", "pms_base", "pms_sale", "queue_job"],
    "data": [
        "views/backend_guesty.xml",
        "views/pms_property.xml",
        "views/pms_property_reservation.xml",
        "views/pms_reservation.xml",
        "views/res_partner.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
}
