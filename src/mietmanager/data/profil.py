from sqlalchemy.orm import Session

from mietmanager.models import Vermieterprofil

PROFIL_ID = 1


def get_or_create_profil(session: Session) -> Vermieterprofil:
    """Liefert das Vermieterprofil, legt es beim ersten Aufruf leer an."""
    profil = session.get(Vermieterprofil, PROFIL_ID)
    if profil is None:
        profil = Vermieterprofil(id=PROFIL_ID)
        session.add(profil)
        session.commit()
    return profil
