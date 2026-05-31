#!/usr/bin/env python3
"""
Deduplicate Person records that share the same name (case-insensitive).

For each duplicate group:
  - Keep the record with the most non-null fields (richest profile)
  - Reassign all EventAttendance rows to the survivor
  - Delete the losers

Run on the Pi:
  cd ~/nytw-guide && python3 server/scripts/dedupe_people.py [--dry-run]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import argparse
from collections import defaultdict
from sqlalchemy import text
from server.db.database import SessionLocal


RICHNESS_SQL = """
    SELECT id, name, company,
        (CASE WHEN company          IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN role             IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN location         IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN photo_url        IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN linkedin_url     IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN twitter_handle   IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN github_handle    IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN instagram_handle IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN bio_snapshot     IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN talking_points   IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN recon_sources    IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN agent_ran_at     IS NOT NULL THEN 1 ELSE 0 END
        ) AS richness
    FROM people
    ORDER BY lower(name), richness DESC
"""


def dedupe(dry_run: bool):
    db = SessionLocal()
    try:
        rows = db.execute(text(RICHNESS_SQL)).fetchall()

        # Group by lowercase name
        groups: dict[str, list] = defaultdict(list)
        for row in rows:
            groups[row.name.strip().lower()].append(row)

        dupes = {k: v for k, v in groups.items() if len(v) > 1}
        if not dupes:
            print("No duplicates found.")
            return

        print(f"Found {len(dupes)} duplicate name(s):\n")
        total_deleted = 0

        for name_key, people in sorted(dupes.items()):
            survivor = people[0]
            losers = people[1:]

            print(f"  '{survivor.name}'  ({len(people)} records)")
            print(f"    KEEP  id={survivor.id}  richness={survivor.richness}"
                  f"  company={survivor.company!r}")

            loser_ids = []
            for loser in losers:
                att_count = db.execute(
                    text("SELECT COUNT(*) FROM event_attendances WHERE person_id = :pid"),
                    {"pid": str(loser.id)}
                ).scalar()
                print(f"    DROP  id={loser.id}  richness={loser.richness}"
                      f"  company={loser.company!r}  attendances={att_count}")
                loser_ids.append(str(loser.id))

            if dry_run:
                continue

            # Reassign attendances that don't conflict
            for loser_id in loser_ids:
                # Find loser's attendances that would conflict with survivor
                conflicts = db.execute(text("""
                    SELECT l.id
                    FROM event_attendances l
                    JOIN event_attendances s ON s.person_id = :survivor_id AND s.event_id = l.event_id
                    WHERE l.person_id = :loser_id
                """), {"survivor_id": str(survivor.id), "loser_id": loser_id}).fetchall()

                conflict_ids = {r.id for r in conflicts}

                # Delete conflicting attendances from loser (survivor already has them)
                if conflict_ids:
                    ids_in = ", ".join(f"'{i}'" for i in conflict_ids)
                    db.execute(text(f"DELETE FROM event_attendances WHERE id IN ({ids_in})"))

                # Reassign the rest
                db.execute(text("""
                    UPDATE event_attendances
                    SET person_id = :survivor_id
                    WHERE person_id = :loser_id
                """), {"survivor_id": str(survivor.id), "loser_id": loser_id})

            # Merge missing fields from losers into survivor (raw SQL UPDATE with COALESCE)
            for loser_id in loser_ids:
                db.execute(text("""
                    UPDATE people SET
                        company          = COALESCE(people.company,          l.company),
                        role             = COALESCE(people.role,             l.role),
                        location         = COALESCE(people.location,         l.location),
                        photo_url        = COALESCE(people.photo_url,        l.photo_url),
                        linkedin_url     = COALESCE(people.linkedin_url,     l.linkedin_url),
                        twitter_handle   = COALESCE(people.twitter_handle,   l.twitter_handle),
                        github_handle    = COALESCE(people.github_handle,    l.github_handle),
                        instagram_handle = COALESCE(people.instagram_handle, l.instagram_handle),
                        personal_site    = COALESCE(people.personal_site,    l.personal_site),
                        email            = COALESCE(people.email,            l.email),
                        bio_snapshot     = COALESCE(people.bio_snapshot,     l.bio_snapshot),
                        talking_points   = COALESCE(people.talking_points,   l.talking_points),
                        recon_sources    = COALESCE(people.recon_sources,    l.recon_sources),
                        raw_intel        = COALESCE(people.raw_intel,        l.raw_intel),
                        agent_ran_at     = COALESCE(people.agent_ran_at,     l.agent_ran_at)
                    FROM people l
                    WHERE people.id = :survivor_id AND l.id = :loser_id
                """), {"survivor_id": str(survivor.id), "loser_id": loser_id})

            # Delete losers
            ids_in = ", ".join(f"'{i}'" for i in loser_ids)
            db.execute(text(f"DELETE FROM people WHERE id IN ({ids_in})"))

            total_deleted += len(loser_ids)

        if not dry_run:
            db.commit()
            print(f"\nDeleted {total_deleted} duplicate record(s). Done.")
        else:
            print(f"\n[dry-run] Would delete {sum(len(v)-1 for v in dupes.values())} record(s).")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without changing anything")
    args = parser.parse_args()
    dedupe(dry_run=args.dry_run)
