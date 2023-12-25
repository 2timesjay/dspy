import inspect
import dspy

from typing import Annotated


from pydantic import create_model, BaseModel, Field
from pydantic.fields import FieldInfo
import inspect, json
from inspect import Parameter


def get_field_type(annotation):
    if hasattr(annotation, '__origin__'):
        # For complex types with __origin__
        field_type = annotation.__origin__
    else:
        # For basic types like str, int, etc.
        field_type = annotation
    return field_type

# # https://stackoverflow.com/questions/49171189/whats-the-correct-way-to-check-if-an-object-is-a-typing-generic
# def function_to_pydantic_model(func):
#     sig = inspect.signature(func)
#     params = sig.parameters
#     annotations = {}

#     for name, param in params.items():
#         description = (
#             param.annotation.__metadata__[0] 
#             if hasattr(param.annotation, '__metadata__') 
#             else "No description"
#         )
#         annotations[name] = (get_field_type(param.annotation), Field(default=..., annotation=get_field_type(param.annotation), description=description))
    
#     return_desc = "No description"
#     return_type = sig.return_annotation
#     if hasattr(return_type, '__metadata__'):
#         return_desc = return_type.__metadata__[0]

#     annotations['return'] = (get_field_type(return_type), Field(default=..., annotation=get_field_type(return_type), description=return_desc))

#     print(annotations)

#     return type(f"{func.__name__.capitalize()}Model", (BaseModel,), annotations)

def function_to_pydantic_model(func):
    sig = inspect.signature(func)
    parameters = sig.parameters
    field_definitions = {
        name: (param.annotation, ... if param.default==Parameter.empty else param.default)
        for name, param in parameters.items()
    }
    
    return_annotation = sig.return_annotation
    field_definitions['return'] = (return_annotation, ... if return_annotation==inspect._empty else None)

    return create_model(f"{func.__name__.capitalize()}Model", **field_definitions)

def pydantic_model_to_dspy_signature(model, return_name=None):
    attrs = {}
    for name, field in model.__fields__.items():
        if name == "return":
            return_name = return_name if return_name else "return"
            attrs[return_name] = dspy.OutputField(desc=field.metadata[0])
        else:
            attrs[name] = dspy.InputField(desc=field.metadata[0])

    return type(f"{model.__name__}".replace("Model", "Signature"), (dspy.Signature,), attrs)


def function_to_dspy_signature(func):
    sig = inspect.signature(func)
    params = sig.parameters
    return_type = sig.return_annotation

    attrs = {}
    for name, param in params.items():
        param_desc = "No description"
        if hasattr(param.annotation, '__metadata__'):
            param_desc = param.annotation.__metadata__[0]
        attrs[name] = dspy.InputField(desc=param_desc)

    return_desc = "No description"
    if hasattr(return_type, '__metadata__'):
        return_desc = return_type.__metadata__[0]

    if return_type is not inspect._empty:
        attrs['return'] = dspy.OutputField(desc=return_desc)

    return type(f"{func.__name__.capitalize()}Signature", (dspy.Signature,), attrs)

def schema(f):
    kw = {n:(o.annotation, ... if o.default==Parameter.empty else o.default)
          for n,o in inspect.signature(f).parameters.items()}
    s = create_model(f'Input for `{f.__name__}`', **kw).schema()
    return dict(name=f.__name__, description=f.__doc__, parameters=s)


def dspy_signature_to_pydantic_model(signature: dspy.Signature, return_name: str = None):
    signature_fields = signature.signature.__dict__
    return_name = return_name if return_name else "return"
    field_definitions = {
        name: (Annotated[str, field.desc], ...)
        for name, field in signature_fields.items()
        if name != return_name
    }
    field_definitions['return'] = (Annotated[str, signature_fields[return_name].desc], ...)

    return create_model(f"{signature.__name__}".replace("Signature", "Model"), **field_definitions)