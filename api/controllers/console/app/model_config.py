import json

from flask import request
from flask_login import current_user
from flask_restful import Resource, reqparse

from controllers.console import api
from controllers.console.app.wraps import get_app_model
from controllers.console.setup import setup_required
from controllers.console.wraps import account_initialization_required
from core.entities.application_entities import AgentToolEntity
from core.tools.tool_manager import ToolManager
from core.tools.utils.configuration import ToolParameterConfigurationManager
from events.app_event import app_model_config_was_updated
from extensions.ext_database import db
from libs.login import login_required
from models.model import AppMode, AppModelConfig
from services.app_model_config_service import AppModelConfigService


class ModelConfigResource(Resource):

    @setup_required
    @login_required
    @account_initialization_required
    @get_app_model(mode=[AppMode.AGENT_CHAT, AppMode.CHAT, AppMode.COMPLETION])
    def post(self, app_model):
        """Modify app model config"""
        # validate config
        model_configuration = AppModelConfigService.validate_configuration(
            tenant_id=current_user.current_tenant_id,
            config=request.json,
            app_mode=AppMode.value_of(app_model.mode)
        )

        new_app_model_config = AppModelConfig(
            app_id=app_model.id,
        )
        new_app_model_config = new_app_model_config.from_model_config_dict(model_configuration)

        # get original app model config
        original_app_model_config: AppModelConfig = db.session.query(AppModelConfig).filter(
            AppModelConfig.id == app.app_model_config_id
        ).first()
        agent_mode = original_app_model_config.agent_mode_dict
        # decrypt agent tool parameters if it's secret-input
        parameter_map = {}
        masked_parameter_map = {}
        tool_map = {}
        for tool in agent_mode.get('tools') or []:
            if not isinstance(tool, dict) or len(tool.keys()) <= 3:
                continue
            
            agent_tool_entity = AgentToolEntity(**tool)
            # get tool
            try:
                tool_runtime = ToolManager.get_agent_tool_runtime(
                    tenant_id=current_user.current_tenant_id,
                    agent_tool=agent_tool_entity,
                    agent_callback=None
                )
                manager = ToolParameterConfigurationManager(
                    tenant_id=current_user.current_tenant_id,
                    tool_runtime=tool_runtime,
                    provider_name=agent_tool_entity.provider_id,
                    provider_type=agent_tool_entity.provider_type,
                )
            except Exception as e:
                continue

            # get decrypted parameters
            if agent_tool_entity.tool_parameters:
                parameters = manager.decrypt_tool_parameters(agent_tool_entity.tool_parameters or {})
                masked_parameter = manager.mask_tool_parameters(parameters or {})
            else:
                parameters = {}
                masked_parameter = {}

            key = f'{agent_tool_entity.provider_id}.{agent_tool_entity.provider_type}.{agent_tool_entity.tool_name}'
            masked_parameter_map[key] = masked_parameter
            parameter_map[key] = parameters
            tool_map[key] = tool_runtime

        # encrypt agent tool parameters if it's secret-input
        agent_mode = new_app_model_config.agent_mode_dict
        for tool in agent_mode.get('tools') or []:
            agent_tool_entity = AgentToolEntity(**tool)
            
            # get tool
            key = f'{agent_tool_entity.provider_id}.{agent_tool_entity.provider_type}.{agent_tool_entity.tool_name}'
            if key in tool_map:
                tool_runtime = tool_map[key]
            else:
                try:
                    tool_runtime = ToolManager.get_agent_tool_runtime(
                        tenant_id=current_user.current_tenant_id,
                        agent_tool=agent_tool_entity,
                        agent_callback=None
                    )
                except Exception as e:
                    continue
            
            manager = ToolParameterConfigurationManager(
                tenant_id=current_user.current_tenant_id,
                tool_runtime=tool_runtime,
                provider_name=agent_tool_entity.provider_id,
                provider_type=agent_tool_entity.provider_type,
            )
            manager.delete_tool_parameters_cache()

            # override parameters if it equals to masked parameters
            if agent_tool_entity.tool_parameters:
                if key not in masked_parameter_map:
                    continue

                if agent_tool_entity.tool_parameters == masked_parameter_map[key]:
                    agent_tool_entity.tool_parameters = parameter_map[key]

            # encrypt parameters
            if agent_tool_entity.tool_parameters:
                tool['tool_parameters'] = manager.encrypt_tool_parameters(agent_tool_entity.tool_parameters or {})

        # update app model config
        new_app_model_config.agent_mode = json.dumps(agent_mode)

        db.session.add(new_app_model_config)
        db.session.flush()

        app_model.app_model_config_id = new_app_model_config.id
        db.session.commit()

        app_model_config_was_updated.send(
            app_model,
            app_model_config=new_app_model_config
        )

        return {'result': 'success'}


class FeaturesResource(Resource):

        @setup_required
        @login_required
        @account_initialization_required
        @get_app_model(mode=[AppMode.ADVANCED_CHAT, AppMode.WORKFLOW])
        def put(self, app_model):
            """Get app features"""
            parser = reqparse.RequestParser()
            parser.add_argument('features', type=dict, required=True, nullable=False, location='json')
            args = parser.parse_args()

            model_configuration = AppModelConfigService.validate_features(
                tenant_id=current_user.current_tenant_id,
                config=args.get('features'),
                app_mode=AppMode.value_of(app_model.mode)
            )

            # update config
            app_model_config = app_model.app_model_config
            app_model_config.from_model_config_dict(model_configuration)
            db.session.commit()

            app_model_config_was_updated.send(
                app_model,
                app_model_config=app_model_config
            )

            return {
                'result': 'success'
            }


api.add_resource(ModelConfigResource, '/apps/<uuid:app_id>/model-config')
api.add_resource(FeaturesResource, '/apps/<uuid:app_id>/features')
