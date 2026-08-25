"""Tests for the Prowler documentation tools.

A failed request must not reach an agent as "the documentation has nothing on
this", which is an answer it would act on, confidently and wrongly.
"""

from fastmcp import Client

SEARCH = "/api/chunk_group/group_oriented_autocomplete"
DOC = "/getting-started/installation.md"


def stub_search_hit(docs_router, path: str = "getting-started/installation"):
    """Serve one Mintlify result group for the search endpoint."""
    return docs_router.add(
        "POST",
        SEARCH,
        json={
            "results": [
                {
                    "group": {"name": path},
                    "chunks": [
                        {
                            "chunk": {"metadata": {"title": "Installation"}},
                            "highlights": ["<mark><b>install</b></mark> prowler"],
                            "score": 0.9,
                        }
                    ],
                }
            ]
        },
    )


async def test_search_returns_the_matching_pages(mcp_root_server, docs_router):
    """The happy path, so the failure tests are not the only coverage."""
    stub_search_hit(docs_router)

    async with Client(mcp_root_server) as client:
        result = await client.call_tool("prowler_docs_search", {"term": "install"})

    assert result.data[0]["path"] == "getting-started/installation"
    assert result.data[0]["url"].endswith("/getting-started/installation")


async def test_a_search_that_failed_is_not_reported_as_no_matches(
    mcp_root_server, docs_router
):
    """An empty list is an answer. A failed request is not, and must not look like one."""
    docs_router.add("POST", SEARCH, status=500, text="upstream error")

    async with Client(mcp_root_server) as client:
        result = await client.call_tool_mcp("prowler_docs_search", {"term": "install"})

    assert result.isError is True
    assert result.structuredContent is None


async def test_a_missing_page_fails_and_names_the_tool_that_finds_a_valid_path(
    mcp_root_server, docs_router
):
    """A 404 answers the question, and still reaches the agent as an error."""
    docs_router.add("GET", DOC, status=404, text="Not Found")

    async with Client(mcp_root_server) as client:
        result = await client.call_tool_mcp(
            "prowler_docs_get_document", {"doc_path": "getting-started/installation"}
        )

    assert result.isError is True
    assert "prowler_docs_search" in result.content[0].text


async def test_a_fetch_that_failed_is_not_reported_as_a_missing_page(
    mcp_root_server, docs_router
):
    """Only a 404 answers the question; every other status left it unanswered."""
    docs_router.add("GET", DOC, status=503, text="upstream error")

    async with Client(mcp_root_server) as client:
        result = await client.call_tool_mcp(
            "prowler_docs_get_document", {"doc_path": "getting-started/installation"}
        )

    assert result.isError is True
    assert "no page at" not in result.content[0].text
