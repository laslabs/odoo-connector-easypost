# -*- coding: utf-8 -*-
# © 2015 LasLabs Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from openerp import models, fields, api
from openerp.addons.connector.unit.mapper import (mapping,
                                                  changed_by,
                                                  only_create,
                                                  )
from ..unit.backend_adapter import EasypostCRUDAdapter
from ..unit.mapper import (EasypostImportMapper,
                           EasypostExportMapper,
                           )
from ..backend import easypost
from ..unit.import_synchronizer import (EasypostImporter)
from ..unit.export_synchronizer import (EasypostExporter)
from ..unit.mapper import eval_false


_logger = logging.getLogger(__name__)


class EasypostEasypostAddress(models.TransientModel):
    """ Binding Model for the Easypost EasypostAddress

        TransientModel so that records are eventually deleted due to immutable
        EasyPost objects
    """
    _name = 'easypost.easypost.address'
    _inherit = 'easypost.binding'
    _inherits = {'easypost.address': 'odoo_id'}
    _description = 'Easypost EasypostAddress'
    _easypost_model = 'Address'

    odoo_id = fields.Many2one(
        comodel_name='easypost.address',
        string='EasypostAddress',
        required=True,
        ondelete='cascade',
    )

    _sql_constraints = [
        ('odoo_uniq', 'unique(backend_id, odoo_id)',
         'A Easypost binding for this patient already exists.'),
    ]

    @api.model
    def _get_by_partner(self, partner_id):
        return self.search([
            ('partner_id', '=', partner_id.id),
        ],
            limit=1,
        )


class EasypostAddress(models.TransientModel):
    """ Adds the ``one2many`` relation to the Easypost bindings
    (``easypost_bind_ids``)
    """
    _inherit = 'easypost.address'

    easypost_bind_ids = fields.One2many(
        comodel_name='easypost.easypost.address',
        inverse_name='odoo_id',
        string='Easypost Bindings',
    )


@easypost
class EasypostAddressAdapter(EasypostCRUDAdapter):
    """ Backend Adapter for the Easypost EasypostAddress """
    _model_name = 'easypost.easypost.address'

    def read(self, _id):
        """ Gets record by id and returns the object
        :param _id: Id of record to get from Db
        :type _id: int
        :return: EasyPost record for model
        """
        return self._get_ep_model().verify(id=_id)


@easypost
class EasypostAddressImportMapper(EasypostImportMapper):
    _model_name = 'easypost.easypost.address'

    direct = [
        (eval_false('street1'), 'street'),
        (eval_false('street2'), 'street2'),
        (eval_false('name'), 'name'),
        (eval_false('email'), 'email'),
        (eval_false('phone'), 'phone'),
        (eval_false('city'), 'city'),
        (eval_false('zip'), 'zip'),
        (eval_false('mode'), 'mode'),
    ]

    @mapping
    @only_create
    def state_id(self, record):
        state_id = self.env['res.country.state'].search([
            ('name', '=', record.state),
        ],
            limit=1,
        )
        return {'state_id': state_id.id}

    @mapping
    @only_create
    def country_id(self, record):
        country_id = self.env['res.country'].search([
            ('code', '=', record.country),
        ],
            limit=1,
        )
        return {'country_id': country_id.id}


@easypost
class EasypostAddressImporter(EasypostImporter):
    _model_name = ['easypost.easypost.address']
    _base_mapper = EasypostAddressImportMapper


@easypost
class EasypostAddressExportMapper(EasypostExportMapper):
    _model_name = 'easypost.easypost.address'

    direct = [
        ('name', 'name'),
        ('street', 'street1'),
        ('street2', 'street2'),
        ('city', 'city'),
        ('zip', 'zip'),
        ('phone', 'phone'),
        ('email', 'email'),
        ('mode', 'mode'),
    ]

    @mapping
    def verify(self, record):
        return {'verify': ['delivery']}

    @mapping
    @changed_by('company_id')
    def company(self, record):
        return {'company': record.company_id.name}

    @mapping
    @changed_by('state_id')
    def state(self, record):
        return {'state': record.state_id.name}

    @mapping
    @changed_by('country_id')
    def country(self, record):
        if record.country_id:
            country = record.country_id.code
        else:
            country = record.company_id.country_id.code
        return {'country': country}


@easypost
class EasypostAddressExporter(EasypostExporter):
    _model_name = ['easypost.easypost.address']
    _base_mapper = EasypostAddressExportMapper

    def _after_export(self):
        binding = self.binding_record.with_context(connector_no_export=True)
        importer = self.unit_for(EasypostAddressImporter)
        map_record = importer.mapper.map_record(self.easypost_id)
        update_vals = map_record.values()
        _logger.debug('Writing to %s with %s',
                      self.binding_record, update_vals)
        binding.write(update_vals)