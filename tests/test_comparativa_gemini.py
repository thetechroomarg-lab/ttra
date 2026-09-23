import json
import httpx
import pytest
from web.comparativa_gemini import research_gemini
from tests.test_comparativa import PHONE


def test_gemini_uses_grounding_metadata_not_model_urls():
    source = 'https://support.apple.com/specifications'
    payload = {'model': PHONE['nombre'], 'attributes': [{'key': 'pantalla', 'value': 'Pantalla OLED'}, {'key': 'ram', 'value': 'Dato sin cita'}]}
    text = json.dumps(payload)
    start = text.index('Pantalla OLED')
    def handle(request):
        assert 'key=' not in str(request.url)
        body = json.loads(request.content)
        assert body['tools'] == [{'google_search': {}}]
        assert 'private' not in request.content.decode()
        return httpx.Response(200, json={'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': json.dumps(payload)}]}, 'groundingMetadata': {
            'groundingChunks': [{'web': {'uri': source, 'title': 'Apple'}}],
            'groundingSupports': [{'segment': {'text': 'Pantalla OLED', 'startIndex': start, 'endIndex': start + len('Pantalla OLED')}, 'groundingChunkIndices': [0]}],
            'searchEntryPoint': {'renderedContent': '<div>Google Search</div>'}}}]})
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result = research_gemini(PHONE, 'test-key', client)
    assert result['attributes'][0]['source_urls'] == [source]
    assert result['attributes'][1]['value'] == 'No confirmado'
    assert result['search_suggestions'] == '<div>Google Search</div>'


def test_gemini_rejects_responses_without_grounding():
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': '{}'}]}}]}))) as client:
        with pytest.raises(ValueError):
            research_gemini(PHONE, 'test-key', client)


@pytest.mark.parametrize('storage', ['128 GB', '8 GB'])
def test_grounding_binds_exact_attribute_occurrence_not_substrings(storage):
    payload = {'model': PHONE['nombre'], 'attributes': [{'key': 'ram', 'value': '8 GB'}, {'key': 'almacenamiento', 'value': storage}]}
    text = json.dumps(payload, ensure_ascii=False)
    start = text.rindex(storage)
    def handle(request):
        return httpx.Response(200, json={'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': text}]}, 'groundingMetadata': {
            'groundingChunks': [{'web': {'uri': 'https://support.apple.com/specs', 'title': 'Apple'}}],
            'groundingSupports': [{'segment': {'text': storage, 'startIndex': len(text[:start].encode()), 'endIndex': len(text[:start+len(storage)].encode()), 'partIndex': 0}, 'groundingChunkIndices': [0]}],
            'searchEntryPoint': {'renderedContent': '<div>Google Search</div>'}}}]})
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result = research_gemini(PHONE, 'test-key', client)
    assert result['attributes'][0]['value'] == 'No confirmado'
    assert result['attributes'][1]['value'] == storage


def test_grounding_preserves_utf8_offsets_fences_and_part_index():
    payload = {'model': PHONE['nombre'], 'attributes': [{'key': 'pantalla', 'value': 'Pantalla táctil OLED'}]}
    text = '```json\n' + json.dumps(payload, ensure_ascii=False) + '\n```'
    value = payload['attributes'][0]['value']; start = text.index(value)
    def handle(request):
        return httpx.Response(200, json={'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': 'Busqué información.'}, {'text': text}]}, 'groundingMetadata': {
            'groundingChunks': [{'web': {'uri': 'https://support.apple.com/specs', 'title': 'Apple'}}],
            'groundingSupports': [{'segment': {'text': value, 'startIndex': len(text[:start].encode()), 'endIndex': len(text[:start+len(value)].encode()), 'partIndex': 1}, 'groundingChunkIndices': [0]}],
            'searchEntryPoint': {'renderedContent': '<div>Google Search</div>'}}}]})
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result = research_gemini(PHONE, 'test-key', client)
    assert result['attributes'][0]['value'] == value
