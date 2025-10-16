from odoo import models,fields,api,_

class ProjectTaskType(models.Model):
    _inherit='project.task.type'

    is_custom_task_type = fields.Boolean(default=False)