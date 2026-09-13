"""ROTA-T024-TESTER-LOGIN-ISOLATION (brief.md exact SHA 9246fad): CENTRAL_SERVICE-only
login + per-account database isolation, built on fastapi-users. Never imported
when api.config.IS_CENTRAL_SERVICE is False -- LOCAL_WINDOWS keeps its
existing unauthenticated single-user behavior untouched (brief section 9/11).
"""
