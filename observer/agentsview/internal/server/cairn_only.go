package server

import (
	"context"
	"net/http"
	"os"
	"sort"
	"strings"

	"github.com/wesm/agentsview/internal/cairn"
	"github.com/wesm/agentsview/internal/db"
	"github.com/wesm/agentsview/internal/service"
)

func cairnOnlyEnabled() bool {
	v := os.Getenv("CAIRN_ONLY")
	return v == "1" || v == "true" || v == "TRUE"
}

type cairnSessionMeta struct {
	Project string
	Title   string
}

func (s *Server) cairnSessionIDs(ctx context.Context) (map[string]struct{}, error) {
	sessions, err := s.cairnSessions(ctx)
	if err != nil {
		return nil, err
	}
	ids := make(map[string]struct{}, len(sessions))
	for id := range sessions {
		ids[id] = struct{}{}
	}
	return ids, nil
}

func (s *Server) cairnSessions(ctx context.Context) (map[string]cairnSessionMeta, error) {
	runs, err := cairn.ListRuns(ctx, cairn.RunsDirFromEnv(), cairn.ListFilter{})
	if err != nil {
		return nil, err
	}
	summaries, err := cairn.ProjectSummaries(ctx, cairn.DBPathFromEnv())
	if err != nil {
		return nil, err
	}
	sessions := make(map[string]cairnSessionMeta, len(runs))
	for _, run := range runs {
		summary, ok := summaries[run.ProjectID]
		if !ok {
			summary = cairn.ProjectSummary{Title: run.ProjectID}
		}
		if run.SessionID != nil && *run.SessionID != "" {
			meta := cairnSessionMeta{
				Project: cairnProjectName(run.ProjectID),
				Title:   cairnSessionTitle(run, summary),
			}
			if _, exists := sessions[*run.SessionID]; !exists {
				sessions[*run.SessionID] = meta
			}
			for _, id := range cairnSessionIDVariants(run.AgentType, *run.SessionID) {
				if _, exists := sessions[id]; !exists {
					sessions[id] = meta
				}
			}
		}
	}
	return sessions, nil
}

func cairnSessionTitle(run cairn.Run, summary cairn.ProjectSummary) string {
	var title string
	switch {
	case strings.HasPrefix(run.Phase, "explore"):
		if run.IntentID != nil {
			title = cairnExploreTitle(*run.IntentID, summary)
		}
	case strings.HasPrefix(run.Phase, "reason"):
		title = cairnReasonTitle(run, summary)
	case strings.HasPrefix(run.Phase, "bootstrap"):
		title = cairnBootstrapTitle(run, summary)
	default:
		if run.IntentID != nil {
			title = cairnExploreTitle(*run.IntentID, summary)
		}
	}
	return shortenTitle(firstNonEmpty(title, summary.Title))
}

func cairnBootstrapTitle(run cairn.Run, summary cairn.ProjectSummary) string {
	if run.IntentID != nil {
		if intent, ok := summary.Intents[*run.IntentID]; ok {
			if factTitle := cairnFactTitle(intent.ToFactID, summary); factTitle != "" {
				if strings.HasPrefix(run.Phase, "bootstrap_conclude") || run.Status == "success" {
					return "事实: " + factTitle
				}
			}
		}
	}
	title := joinTitleParts(summary.Goal, summary.Origin)
	if title != "" {
		return "起步: " + title
	}
	return title
}

func cairnReasonTitle(run cairn.Run, summary cairn.ProjectSummary) string {
	if run.IntentID != nil {
		if intent, ok := summary.Intents[*run.IntentID]; ok && intent.ToFactID == "goal" {
			return "完成: " + firstNonEmpty(cairnFactTitle(intent.ToFactID, summary), summary.Goal, summary.Title)
		}
	}
	title := firstNonEmpty(summary.Goal, summary.Title)
	if title != "" {
		return "计划: " + title
	}
	return title
}

func cairnExploreTitle(intentID string, summary cairn.ProjectSummary) string {
	intent, ok := summary.Intents[intentID]
	if !ok {
		return ""
	}
	if factTitle := cairnFactTitle(intent.ToFactID, summary); factTitle != "" {
		return "事实: " + factTitle
	}
	if intent.Description != "" {
		return "探索: " + intent.Description
	}
	return ""
}

func cairnFactTitle(factID string, summary cairn.ProjectSummary) string {
	factID = strings.TrimSpace(factID)
	if factID == "" {
		return ""
	}
	if factID == "goal" {
		return firstNonEmpty(summary.Goal, summary.Title)
	}
	return summary.Facts[factID]
}

func joinTitleParts(parts ...string) string {
	kept := make([]string, 0, len(parts))
	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part != "" {
			kept = append(kept, part)
		}
	}
	return strings.Join(kept, ": ")
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value != "" {
			return value
		}
	}
	return ""
}

func shortenTitle(title string) string {
	title = strings.Join(strings.Fields(title), " ")
	const limit = 80
	if len([]rune(title)) <= limit {
		return title
	}
	runes := []rune(title)
	return string(runes[:limit-1]) + "…"
}

func cairnSessionIDVariants(agentType string, sessionID string) []string {
	sessionID = strings.TrimSpace(sessionID)
	if sessionID == "" {
		return nil
	}
	var variants []string
	if prefix, raw, ok := strings.Cut(sessionID, ":"); ok {
		variants = append(variants, raw)
		switch strings.ToLower(strings.TrimSpace(prefix)) {
		case "codex", "claude", "pi":
			variants = append(variants, prefix+":"+raw)
		}
	}
	switch strings.ToLower(strings.TrimSpace(agentType)) {
	case "codex":
		variants = append(variants, "codex:"+strings.TrimPrefix(sessionID, "codex:"))
	case "claudecode", "claude":
		variants = append(variants, "claude:"+strings.TrimPrefix(sessionID, "claude:"))
	case "pi":
		variants = append(variants, "pi:"+strings.TrimPrefix(sessionID, "pi:"))
	}
	return uniqueStrings(variants)
}

func uniqueStrings(values []string) []string {
	seen := make(map[string]struct{}, len(values))
	unique := make([]string, 0, len(values))
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value == "" {
			continue
		}
		if _, exists := seen[value]; exists {
			continue
		}
		seen[value] = struct{}{}
		unique = append(unique, value)
	}
	return unique
}

func cairnProjectName(projectID string) string {
	if projectID == "" {
		return "cairn:unknown"
	}
	return "cairn:" + projectID
}

func (s *Server) cairnAllowsSession(ctx context.Context, id string) (bool, error) {
	if !cairnOnlyEnabled() {
		return true, nil
	}
	ids, err := s.cairnSessionIDs(ctx)
	if err != nil {
		return false, err
	}
	_, ok := ids[id]
	return ok, nil
}

func (s *Server) requireCairnSession(w http.ResponseWriter, r *http.Request, id string) bool {
	ok, err := s.cairnAllowsSession(r.Context(), id)
	if err != nil {
		if handleContextError(w, err) {
			return false
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return false
	}
	if !ok {
		writeError(w, http.StatusNotFound, "session not found")
		return false
	}
	return true
}

func (s *Server) filterCairnSessionPage(
	ctx context.Context,
	page *service.SessionList,
	projectFilter string,
) (*service.SessionList, error) {
	if !cairnOnlyEnabled() {
		return page, nil
	}
	if page == nil {
		return page, nil
	}
	sessions, err := s.cairnSessions(ctx)
	if err != nil {
		return page, err
	}
	filtered := page.Sessions[:0]
	seen := make(map[string]struct{}, len(page.Sessions))
	for _, sess := range page.Sessions {
		if meta, ok := sessions[sess.ID]; ok {
			if projectFilter != "" && meta.Project != projectFilter {
				continue
			}
			applyCairnSessionMeta(&sess, meta)
			filtered = append(filtered, sess)
			seen[sess.ID] = struct{}{}
		}
	}
	if len(filtered) == 0 || len(filtered) < len(sessions) {
		for id, meta := range sessions {
			if _, exists := seen[id]; exists {
				continue
			}
			if projectFilter != "" && meta.Project != projectFilter {
				continue
			}
			sess, err := s.db.GetSession(ctx, id)
			if err != nil {
				return page, err
			}
			if sess == nil {
				continue
			}
			applyCairnSessionMeta(sess, meta)
			filtered = append(filtered, *sess)
			seen[id] = struct{}{}
		}
	}
	page.Sessions = filtered
	page.Total = len(filtered)
	page.NextCursor = ""
	return page, nil
}

func (s *Server) rewriteCairnSessionProject(
	ctx context.Context,
	sess *db.Session,
) error {
	if !cairnOnlyEnabled() || sess == nil {
		return nil
	}
	sessions, err := s.cairnSessions(ctx)
	if err != nil {
		return err
	}
	if meta, ok := sessions[sess.ID]; ok {
		applyCairnSessionMeta(sess, meta)
	}
	return nil
}

func (s *Server) rewriteCairnSessionDetail(
	ctx context.Context,
	detail *service.SessionDetail,
) error {
	if !cairnOnlyEnabled() || detail == nil {
		return nil
	}
	sessions, err := s.cairnSessions(ctx)
	if err != nil {
		return err
	}
	if meta, ok := sessions[detail.ID]; ok {
		applyCairnSessionMeta(&detail.Session, meta)
	}
	return nil
}

func applyCairnSessionMeta(sess *db.Session, meta cairnSessionMeta) {
	sess.Project = meta.Project
	if meta.Title != "" {
		title := meta.Title
		sess.DisplayName = &title
	}
}

func (s *Server) cairnProjectInfos(ctx context.Context) ([]db.ProjectInfo, error) {
	sessions, err := s.cairnSessions(ctx)
	if err != nil {
		return nil, err
	}
	counts := make(map[string]int)
	for sessionID, meta := range sessions {
		sess, err := s.db.GetSession(ctx, sessionID)
		if err != nil {
			return nil, err
		}
		if sess == nil {
			continue
		}
		counts[meta.Project]++
	}
	names := make([]string, 0, len(counts))
	for name := range counts {
		names = append(names, name)
	}
	sort.Strings(names)
	infos := make([]db.ProjectInfo, 0, len(names))
	for _, name := range names {
		infos = append(infos, db.ProjectInfo{
			Name:         name,
			SessionCount: counts[name],
		})
	}
	return infos, nil
}
