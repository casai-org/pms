# Copyright (c) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "PMS - Website Sale",
    "summary": "Allow online booking of your properties",
    "version": "14.0.1.0.0",
    "development_status": "Alpha",
    "category": "Generic Modules/Property Management System",
    "website": "https://github.com/OCA/pms",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": [
        "pms_website",
        "pms_sale",
        "website_sale",
    ],
    "data": [
        "data/data.xml",
        "security/ir.model.access.csv",
        "security/pms_security.xml",
        "views/property_template.xml",
    ],
}
