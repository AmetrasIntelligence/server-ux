# Copyright 2015 Antiun Ingeniería S.L. - Antonio Espinosa
# Copyright 2015-2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# Copyright 2019 brain-tec AG - Olivier Jossen
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, exceptions, fields, models


class IrExportsLine(models.Model):
    _inherit = "ir.exports.line"
    _order = "sequence,id"

    name = fields.Char(
        store=True,
        compute="_compute_name",
        compute_sudo=True,
        inverse="_inverse_name",
        help="Field's technical name.",
    )
    field1_id = fields.Many2one(
        "ir.model.fields", "First field", domain="[('model_id', '=', model1_id)]"
    )
    field2_id = fields.Many2one(
        "ir.model.fields", "Second field", domain="[('model_id', '=', model2_id)]"
    )
    field3_id = fields.Many2one(
        "ir.model.fields", "Third field", domain="[('model_id', '=', model3_id)]"
    )
    field4_id = fields.Many2one(
        "ir.model.fields", "Fourth field", domain="[('model_id', '=', model4_id)]"
    )
    model1_id = fields.Many2one(
        "ir.model",
        "First model",
        readonly=True,
        related="export_id.model_id",
        related_sudo=True,
    )
    model2_id = fields.Many2one(
        "ir.model", "Second model", compute="_compute_model2_id", compute_sudo=True
    )
    model3_id = fields.Many2one(
        "ir.model", "Third model", compute="_compute_model3_id", compute_sudo=True
    )
    model4_id = fields.Many2one(
        "ir.model", "Fourth model", compute="_compute_model4_id", compute_sudo=True
    )
    sequence = fields.Integer()
    label = fields.Char(compute="_compute_label")

    @api.depends("field1_id", "field2_id", "field3_id", "field4_id")
    def _compute_name(self):
        """Get the name from the selected fields."""
        for one in self:
            name = "/".join(
                one.field_n(num).name for num in range(1, 5) if one.field_n(num)
            )
            if name != one.name:
                one.name = name

    @api.depends("field1_id")
    def _compute_model2_id(self):
        """Get the related model for the second field."""
        IrModel = self.env["ir.model"].sudo()
        for one in self:
            one.model2_id = (
                one.field1_id.ttype
                and "2" in one.field1_id.ttype
                and IrModel.search([("model", "=", one.field1_id.relation)])
            )

    @api.depends("field2_id")
    def _compute_model3_id(self):
        """Get the related model for the third field."""
        IrModel = self.env["ir.model"].sudo()
        for one in self:
            one.model3_id = (
                one.field2_id.ttype
                and "2" in one.field2_id.ttype
                and IrModel.search([("model", "=", one.field2_id.relation)])
            )

    @api.depends("field3_id")
    def _compute_model4_id(self):
        """Get the related model for the third field."""
        IrModel = self.env["ir.model"].sudo()
        for one in self:
            one.model4_id = (
                one.field3_id.ttype
                and "2" in one.field3_id.ttype
                and IrModel.search([("model", "=", one.field3_id.relation)])
            )

    @api.depends("name")
    def _compute_label(self):
        """Column label in a user-friendly format and language."""
        for one in self:
            parts = list()
            for num in range(1, 5):
                field = one.field_n(num)
                if not field:
                    break
                # Translate label if possible
                try:
                    parts.append(
                        one.env[one.model_n(num).model]
                        ._fields[field.name]
                        .get_description(one.env)["string"]
                    )
                except KeyError:
                    # No human-readable string available, so empty this
                    parts = []
                    break
            one.label = (
                "{} ({})".format("/".join(parts), one.name)
                if parts and one.name
                else False
            )

    def _inverse_name(self):
        """Get the fields from the name."""
        for one in self:
            # Field names can have up to only 4 indentation levels
            parts = (one.name or "").split("/")
            if len(parts) > 4:
                raise exceptions.ValidationError(
                    _("It's not allowed to have more than 4 levels depth: %s")
                    % one.name
                )
            for num in range(1, 5):
                if not any(parts) or num > len(parts):
                    # Empty subfield in this case
                    # You could get to failing constraint while populating the
                    # fields, so we skip the uniqueness check and manually
                    # check the full constraint after the loop
                    one.with_context(skip_check=True)[one.field_n(num, True)] = False
                    continue
                field_name = parts[num - 1]
                model = one.model_n(num)
                # You could get to failing constraint while populating the
                # fields, so we skip the uniqueness check and manually check
                # the full constraint after the loop
                one.with_context(skip_check=True)[
                    one.field_n(num, True)
                ] = one._get_field_id(model, field_name)
            if any(parts):
                # invalidate_recordset -> in order to get actual value of field 'label'
                # in function '_check_name'
                one.invalidate_recordset(["label"])
                one._check_name()

    @api.constrains("field1_id", "field2_id", "field3_id", "field4_id")
    def _check_name(self):
        # do also skip the check if label is set or not, when skip_check is set
        if self._context.get("skip_check"):
            return
        for one in self:
            if not one.label:
                raise exceptions.ValidationError(
                    _("Field '%s' does not exist") % one.name
                )
            num_lines = one.search_count(
                [("export_id", "=", one.export_id.id), ("name", "=", one.name)]
            )
            if num_lines > 1:
                raise exceptions.ValidationError(
                    _("Field '%s' already exists") % one.name
                )

    @api.model
    def _get_field_id(self, model, name):
        """Get a field object from its model and name.

        :param int model:
            ``ir.model`` object that contains the field.

        :param str name:
            Technical name of the field, like ``child_ids``.
        """

        # Handle special case "id" field
        name = "id" if name == ".id" else name

        field = (
            self.env["ir.model.fields"]
            .sudo()
            .search([("name", "=", name), ("model_id", "=", model.id)])
        )
        if not field.exists():
            raise exceptions.ValidationError(
                _("Field '%(name)s' not found in model '%(model)s'")
                % {"name": name, "model": model.model}
            )
        return field

    def field_n(self, n, only_name=False):
        """Helper to choose the field according to its indentation level.

        :param int n:
            Number of the indentation level to choose the field, from 1 to 3.

        :param bool only_name:
            Return only the field name, or return its value.
        """
        name = "field%d_id" % n
        return name if only_name else self[name]

    def model_n(self, n, only_name=False):
        """Helper to choose the model according to its indentation level.

        :param int n:
            Number of the indentation level to choose the model, from 1 to 3.

        :param bool only_name:
            Return only the model name, or return its value.
        """
        name = "model%d_id" % n
        return name if only_name else self[name]
