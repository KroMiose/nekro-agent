import pytest
import nekro_agent

def test_import():
    """Test that the package can be imported."""
    assert nekro_agent is not None

def test_client_initialization():
    """Test that the client can be initialized."""
    client = nekro_agent.Client()
    assert client is not None

@pytest.mark.asyncio
async def test_async_client():
    """Test async client initialization."""
    client = nekro_agent.AsyncClient()
    assert client is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
