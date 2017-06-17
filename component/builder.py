# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

"""

Components Builder
==================

Build the components at the build of a registry.

"""

import odoo
from odoo import api, models
from .core import MetaComponent, _component_databases


class ComponentBuilder(models.AbstractModel):
    """ Build the component classes

    And register them in a global registry.

    Every time an Odoo registry is built, the know components are cleared and
    rebuilt as well.  The Component classes are built using the same mechanism
    than Odoo's Models: a final class is created, taking every Components with
    a ``_name`` and applying Components with an ``_inherits`` upon them.

    The final Component classes are registered in global registry.

    This class is an Odoo model, allowing us to hook the build of the
    components at the end of the Odoo's registry loading, using
    ``_register_hook``. This method is called after all modules are loaded, so
    we are sure that we have all the components Classes and in the correct
    order.

    """
    _name = 'component.builder'
    _description = 'Component Builder'

    @api.model_cr
    def _register_hook(self):
        # This method is called by Odoo when the registry is built,
        # so in case the registry is rebuilt (cache invalidation, ...),
        # we have to clear the components then rebuild them
        _component_databases.clear(self.env.cr.dbname)
        # TODO: reset the LRU cache of the component lookups when implemented

        # lookup all the installed (or about to be) addons and generate
        # the graph, so we can load the components following the order
        # of the addons' dependencies
        graph = odoo.modules.graph.Graph()
        graph.add_module(self.env.cr, 'base')

        self.env.cr.execute(
            "SELECT name "
            "FROM ir_module_module "
            "WHERE state IN ('installed', 'to upgrade', 'to update')"
        )
        module_list = [name for (name,) in self.env.cr.fetchall()
                       if name not in graph]
        graph.add_modules(self.env.cr, module_list)

        components_registry = _component_databases[self.env.cr.dbname]
        for module in graph:
            self.load_components(module.name, components_registry)

    def load_components(self, module, components_registry):
        """ Build every component known by MetaComponent for an odoo module

        The final component (composed by all the Component classes in this
        module) will be pushed into the registry.

        :param module: the name of the addon for which we want to load
                       the components
        :type module: str | unicode
        :param registry: the registry in which we want to put the Component
        :type registry: :py:class:`~.core.ComponentRegistry`
        """
        for component_class in MetaComponent._modules_components[module]:
            component_class._build_component(components_registry)
