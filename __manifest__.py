# See LICENSE file for full copyright and licensing details.
{
    'name': 'Do An Tot Nghiep',
    'version': "12.0.1.0.0",
    'author': "Nguyen Quang Duy",
    'category': 'School Management',
    'license': "AGPL-3",
    'summary': 'A Module For Library Management For School',
    'complexity': 'easy',
    'depends': ['base', 'mail', 'muk_web_searchpanel'],
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/library_menu.xml',
        'views/author.xml',
        'views/publisher.xml',
        'views/category.xml',
        'views/member.xml',
        'views/card.xml',
        'data/library_card_schedular.xml',
        'views/book.xml',
        'views/project.xml',
        'views/magazine_newspaper.xml',
        'views/checkout.xml',
        'reports/library_card_report.xml',
        'reports/library_checkout_report.xml',
    ],
    # 'demo': ['demo/data.xml'],
    # 'image': ['static/description/SchoolLibrary.png'],
    'installable': True,
    'application': True
}
