package cairn

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"net/url"
	"os"

	_ "github.com/mattn/go-sqlite3"
)

func DBPathFromEnv() string {
	return os.Getenv("CAIRN_DB_PATH")
}

type ProjectSummary struct {
	Title   string
	Origin  string
	Goal    string
	Intents map[string]string
}

func ProjectSummaries(ctx context.Context, dbPath string) (map[string]ProjectSummary, error) {
	if dbPath == "" {
		return nil, nil
	}
	if _, err := os.Stat(dbPath); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, nil
		}
		return nil, fmt.Errorf("stat Cairn db: %w", err)
	}
	u := url.URL{Scheme: "file", Path: dbPath}
	q := u.Query()
	q.Set("mode", "ro")
	q.Set("immutable", "1")
	u.RawQuery = q.Encode()
	db, err := sql.Open("sqlite3", u.String())
	if err != nil {
		return nil, fmt.Errorf("open Cairn db: %w", err)
	}
	defer db.Close()

	rows, err := db.QueryContext(ctx, "SELECT id, title FROM projects")
	if err != nil {
		return nil, fmt.Errorf("query Cairn project titles: %w", err)
	}
	defer rows.Close()

	summaries := make(map[string]ProjectSummary)
	for rows.Next() {
		var id, title string
		if err := rows.Scan(&id, &title); err != nil {
			return nil, fmt.Errorf("scan Cairn project title: %w", err)
		}
		if id != "" && title != "" {
			summaries[id] = ProjectSummary{
				Title:   title,
				Intents: make(map[string]string),
			}
		}
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate Cairn project titles: %w", err)
	}
	if err := loadFacts(ctx, db, summaries); err != nil {
		return nil, err
	}
	if err := loadIntents(ctx, db, summaries); err != nil {
		return nil, err
	}
	return summaries, nil
}

func loadFacts(ctx context.Context, db *sql.DB, summaries map[string]ProjectSummary) error {
	rows, err := db.QueryContext(ctx, "SELECT project_id, id, description FROM facts")
	if err != nil {
		return fmt.Errorf("query Cairn facts: %w", err)
	}
	defer rows.Close()
	for rows.Next() {
		var projectID, id, description string
		if err := rows.Scan(&projectID, &id, &description); err != nil {
			return fmt.Errorf("scan Cairn fact: %w", err)
		}
		summary, ok := summaries[projectID]
		if !ok {
			summary = ProjectSummary{Intents: make(map[string]string)}
		}
		switch id {
		case "origin":
			summary.Origin = description
		case "goal":
			summary.Goal = description
		}
		summaries[projectID] = summary
	}
	if err := rows.Err(); err != nil {
		return fmt.Errorf("iterate Cairn facts: %w", err)
	}
	return nil
}

func loadIntents(ctx context.Context, db *sql.DB, summaries map[string]ProjectSummary) error {
	rows, err := db.QueryContext(ctx, "SELECT project_id, id, description FROM intents")
	if err != nil {
		return fmt.Errorf("query Cairn intents: %w", err)
	}
	defer rows.Close()
	for rows.Next() {
		var projectID, id, description string
		if err := rows.Scan(&projectID, &id, &description); err != nil {
			return fmt.Errorf("scan Cairn intent: %w", err)
		}
		summary, ok := summaries[projectID]
		if !ok {
			summary = ProjectSummary{Intents: make(map[string]string)}
		}
		if summary.Intents == nil {
			summary.Intents = make(map[string]string)
		}
		summary.Intents[id] = description
		summaries[projectID] = summary
	}
	if err := rows.Err(); err != nil {
		return fmt.Errorf("iterate Cairn intents: %w", err)
	}
	return nil
}
