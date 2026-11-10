from pathlib import Path


PAGE = Path(__file__).parents[2] / "web" / "app" / "page.tsx"


def test_bilingual_command_center_routes_to_existing_modules_without_publishing() -> None:
    source = PAGE.read_text(encoding="utf-8")
    start = source.index('<section className="command-center"')
    end = source.index("</section>", start) + len("</section>")
    launcher = source[start:end]

    # Both locales expose the same set of already implemented destinations.
    for key in (
        "commandCenter", "launchIdeas", "launchReels", "launchProfile", "launchTrends",
        "launchAnalytics", "launchStrategy", "launchPublishing",
    ):
        assert source.count(f"{key}:") == 2

    for action in (
        'setStudioTab("assistant"); changeView("studio")',
        'setStudioTab("reels"); changeView("studio")',
        'changeView("settings")',
        'setStudioTab("trends"); changeView("studio")',
        'changeView("insights")',
        'setStudioTab("strategy"); changeView("studio")',
        'changeView("calendar")',
    ):
        assert action in launcher

    # Launcher cards only navigate; the publishing approval stays in the calendar workflow.
    assert "approvePost(" not in launcher
    assert "/api/instagram/posts" not in launcher
    assert "setStudioTab(\"strategy\")" in launcher


def test_command_center_truthfully_labels_public_trends_and_approval_gate() -> None:
    source = PAGE.read_text(encoding="utf-8")
    assert "إشارات بحث Google العامة، وليست ترندات Instagram" in source
    assert "Public Google search signals, not Instagram trends" in source
    assert "النشر يظل خلف موافقتك" in source
    assert "publishing still requires your approval" in source
