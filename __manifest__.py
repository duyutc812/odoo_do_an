# See LICENSE file for full copyright and licensing details.
{
    'name': 'Do An Tot Nghiep',
    'version': "12.0.1.0.0",
    'author': "Nguyen Quang Duy",
    'category': 'School Management',
    'license': "AGPL-3",
    'summary': 'A Module For Library Management For School',
    'complexity': 'easy',
    'depends': ['base', 'mail', 'muk_web_searchpanel', 'web_notify'],
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'security/library_security.xml',
        'data/sequence.xml',
        'data/mail_template.xml',
        'views/library_menu.xml',
        'views/library_duration.xml',
        'views/author.xml',
        'views/publisher.xml',
        'views/category.xml',
        'views/member.xml',
        'wizards/extend_library_card.xml',
        'views/card.xml',
        'data/library_card_schedular.xml',
        'wizards/create_meta_book.xml',
        'views/book.xml',
        'wizards/create_meta_project.xml',
        'views/project.xml',
        'views/magazine_newspaper.xml',
        'wizards/modify_descrip.xml',
        'views/checkout_at_lib.xml',
        'views/checkout_back_home.xml',
        'reports/library_card_report.xml',
        'reports/library_checkout_report.xml',
    ],
    # 'demo': ['demo/data.xml'],
    # 'image': ['static/description/SchoolLibrary.png'],
    'installable': True,
    'application': True
}
