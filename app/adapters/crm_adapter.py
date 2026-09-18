"""CRM adapter -- stub only, per PRD Section 14.1/14.1a and solution.json SOL-7.

Ratified unchanged by data_integration decision DAT-7. Returns seeded,
synthetic account/contact data. This system never creates, edits, or deletes
an account or contact record (PRD v1.8 Section 7, Data Ownership NFR) --
every read here is live, in-memory, seeded data standing in for a real CRM
integration that does not exist in this scope.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AdapterAccount:
    id: str
    name: str


@dataclass(frozen=True)
class AdapterContact:
    id: str
    account_id: str
    name: str
    company: str | None
    role: str | None


# Synthetic seed data only (CLAUDE.md: never real customer/employee data).
# Names deliberately match the PRD's own canonical example text ("met Priya
# and Arjun from Acme...", idea_input) so that example is a real, working
# demo scenario against this seed data, not just illustrative prose.
_SEEDED_ACCOUNTS: list[AdapterAccount] = [
    AdapterAccount(id="ACC-ACME", name="Acme"),
    AdapterAccount(id="ACC-GLOBEX", name="Globex"),
    AdapterAccount(id="ACC-INITECH", name="Initech"),
]

_SEEDED_CONTACTS: list[AdapterContact] = [
    AdapterContact(id="CON-1", account_id="ACC-ACME", name="Priya Sharma", company="Acme", role="VP Procurement"),
    AdapterContact(id="CON-2", account_id="ACC-ACME", name="Arjun Mehta", company="Acme", role="Technical Lead"),
    AdapterContact(id="CON-3", account_id="ACC-GLOBEX", name="Sam Rivera", company="Globex", role="Director of Operations"),
    AdapterContact(id="CON-4", account_id="ACC-INITECH", name="Jordan Lee", company="Initech", role="CTO"),
]


class CRMAdapter:
    """Stub CRM adapter. Ratified interface per PRD Section 14.1a."""

    def fetch_accounts(self) -> list[AdapterAccount]:
        return list(_SEEDED_ACCOUNTS)

    def fetch_contacts(self, account_id: str) -> list[AdapterContact]:
        return [c for c in _SEEDED_CONTACTS if c.account_id == account_id]

    def find_account_by_name_fragment(self, text: str) -> AdapterAccount | None:
        """Case-insensitive substring match of an account name against free text.

        DATA-MODEL Section 1.4 / Open Item OI-21: full-list, in-memory matching,
        judged acceptable only at this scope's small seeded-dataset size.
        Returns the single unambiguous match, or None if zero or more than one
        account name appears in the text (F-1 AC1: "unambiguously matches
        exactly one seeded customer account").
        """
        text_lower = text.lower()
        matches = [a for a in self.fetch_accounts() if a.name.lower() in text_lower]
        if len(matches) == 1:
            return matches[0]
        return None

    def get_account(self, account_id: str) -> AdapterAccount | None:
        for a in self.fetch_accounts():
            if a.id == account_id:
                return a
        return None


_adapter_singleton = CRMAdapter()


def get_crm_adapter() -> CRMAdapter:
    return _adapter_singleton
