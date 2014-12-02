import os
import hashlib
import json
from django.contrib.staticfiles import finders
from django.utils.safestring import mark_safe
from .exceptions import ReactComponentSourceFileNotFound
from .settings import STATIC_URL, STATIC_ROOT
from .utils import render, bundle


class ReactComponent(object):
    source = None
    # TODO
    # exported_as = None
    props = None
    serialised_props = None
    path_to_bundled_source = None

    def __init__(self, **kwargs):
        self.props = kwargs

    def render(self):
        return self.render_container(
            content=render(self)
        )

    def render_static(self):
        return self.render_container(
            content=render(self, to_static_markup=True)
        )

    def render_js(self):
        rendered_component = '\n'.join((
            self.render_props(),
            self.render_source(),
            self.render_init()
        ))
        return mark_safe(rendered_component)

    def render_container(self, content=None):
        if content is None:
            content = ''
        rendered_mount_element = '<div id="{container_id}" class="{container_class_name}">{content}</div>'.format(
            container_id=self.get_container_id(),
            container_class_name=self.get_container_class_name(),
            content=content,
        )
        return mark_safe(rendered_mount_element)

    def render_props(self):
        rendered_props = '<script>{props_variable} = {serialised_props};</script>'.format(
            props_variable=self.get_props_variable(),
            serialised_props=self.get_serialised_props(),
        )
        return mark_safe(rendered_props)

    def render_source(self):
        rendered_bundle = '<script src="{url_to_mount_bundle}"></script>'.format(
            url_to_mount_bundle=self.get_url_to_source()
        )
        return mark_safe(rendered_bundle)

    def render_init(self):
        props_check = ''
        if self.has_props():
            props_check = '''
                if (!window.{props_variable}) {{
                    throw new Error('Cannot find props `{props_variable}` for component `{exported_variable}`');
                }}
            '''.format(
                props_variable=self.get_props_variable(),
                exported_variable=self.get_component_variable(),
            )
        rendered_mount_script = '''
            <script>
                if (!window.{exported_variable}) {{
                    throw new Error('Cannot find component `{exported_variable}`');
                }}
                {props_check}
                (function(React, component, props, container_id) {{
                    var react_element = React.createElement(component, props);
                    var mount_container = document.getElementById(container_id);
                    if (!mount_container) {{
                        throw new Error('Cannot find the container element `#' + container_id + '` for component `{exported_variable}`');
                    }}
                    React.render(react_element, mount_container);
                }})({react_variable}, {exported_variable}, window.{props_variable}, '{container_id}');
            </script>
        '''.format(
            react_variable=self.get_react_variable(),
            exported_variable=self.get_component_variable(),
            props_variable=self.get_props_variable(),
            container_id=self.get_container_id(),
            props_check=props_check,
        )
        return mark_safe(rendered_mount_script)

    def get_source(self):
        return self.source

    def get_path_to_source(self):
        source = self.get_source()
        path_to_source = finders.find(source)
        if not os.path.exists(path_to_source):
            raise ReactComponentSourceFileNotFound(path_to_source)
        return path_to_source

    def get_props(self):
        return self.props

    def has_props(self):
        if self.get_props():
            return True
        return False

    # TODO
    # def get_exported_as(self):
    #     return self.exported_as

    def get_component_name(self):
        return self.__class__.__name__

    def get_component_variable(self):
        return self.get_component_name()

    def get_react_variable(self):
        return 'React'

    def get_component_id(self):
        return unicode(id(self))

    def get_container_id(self):
        return 'reactComponentContainer-{component_id}'.format(
            component_id=self.get_component_id()
        )

    def get_container_class_name(self):
        return 'reactComponentContainer reactComponentContainer--{component_name}'.format(
            component_name=self.get_component_name()
        )

    def get_serialised_props(self):
        if not self.serialised_props:
            self.serialised_props = json.dumps(self.get_props())
        return self.serialised_props

    def get_serialised_props_hash(self):
        serialised_props = self.get_serialised_props()
        md5 = hashlib.md5()
        md5.update(serialised_props)
        return md5.hexdigest()

    def get_props_variable(self):
        return '__propsFor{component_name}_{serialised_props_hash}__'.format(
            component_name=self.get_component_name(),
            serialised_props_hash=self.get_serialised_props_hash(),
        )

    def get_path_to_bundled_source(self):
        if not self.path_to_bundled_source:
            self.path_to_bundled_source = bundle(self)
        return self.path_to_bundled_source

    def get_url_to_source(self):
        _, rel_path_to_bundled_source = self.get_path_to_bundled_source().split(STATIC_ROOT)
        if rel_path_to_bundled_source[0] in ['/', '\\']:
            rel_path_to_bundled_source = rel_path_to_bundled_source[1:]
        return os.path.join(STATIC_URL, rel_path_to_bundled_source)