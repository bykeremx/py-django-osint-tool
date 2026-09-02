# GitHub profil zenginleştirme.
from __future__ import annotations

import os
from typing import Any

import httpx


class GithubProfileService:
    API_URL = "https://api.github.com/users/{username}"

    @classmethod
    def lookup(cls, username: str) -> dict[str, Any]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "CYBER-OPS-OSINT",
        }
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            with httpx.Client(timeout=12.0, headers=headers) as client:
                response = client.get(cls.API_URL.format(username=username))
                if response.status_code == 404:
                    return cls._not_found(username)
                if response.status_code == 403:
                    return cls._error(username, "GitHub API rate limit — GITHUB_TOKEN ekleyin.")
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            return cls._error(username, f"GitHub API hatası: {e.response.status_code}")
        except Exception as e:
            return cls._error(username, str(e))

        return {
            "error": None,
            "exists": True,
            "username": data.get("login", username),
            "profile_url": data.get("html_url"),
            "avatar_url": data.get("avatar_url"),
            "name": data.get("name"),
            "bio": data.get("bio"),
            "location": data.get("location"),
            "blog": data.get("blog"),
            "company": data.get("company"),
            "public_email": data.get("email"),
            "public_repos": data.get("public_repos"),
            "followers": data.get("followers"),
            "following": data.get("following"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
        }

    @staticmethod
    def _not_found(username: str) -> dict[str, Any]:
        return {
            "error": None,
            "exists": False,
            "username": username,
            "profile_url": None,
            "message": "GitHub'da bu kullanıcı adı bulunamadı.",
        }

    @staticmethod
    def _error(username: str, message: str) -> dict[str, Any]:
        return {
            "error": message,
            "exists": False,
            "username": username,
            "profile_url": None,
        }
