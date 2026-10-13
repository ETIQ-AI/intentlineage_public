"""Version dispatcher contract only; fake objects never qualify a provider."""
import pytest
from intentlineage import experiment_qualification as dispatcher
from intentlineage import experiment_chatgpt as native


@pytest.mark.parametrize('version',['m3b-chatgpt-protocol.1','m3b-chatgpt-function-protocol.1'])
def test_both_chatgpt_formats_delegate_to_the_same_genuine_validator(monkeypatch,version):
 calls=[];packet=object();protocol={'format_version':version};evidence_root=object();sentinel=object()
 def validate(receipt,*,protocol,evidence_root):
  calls.append((receipt,protocol,evidence_root));return sentinel
 monkeypatch.setattr(native,'validate_chatgpt_qualification',validate)
 assert dispatcher.validate_provider_qualification(packet,protocol=protocol,evidence_root=evidence_root) is sentinel
 assert calls==[(packet,protocol,evidence_root)]


def test_function_dispatch_preserves_native_validation_failure(monkeypatch):
 def reject(*args,**kwargs):raise ValueError('Actual native receipt rejected')
 monkeypatch.setattr(native,'validate_chatgpt_qualification',reject)
 with pytest.raises(ValueError,match='Actual native receipt rejected'):
  dispatcher.validate_provider_qualification({},protocol={'format_version':'m3b-chatgpt-function-protocol.1'})
