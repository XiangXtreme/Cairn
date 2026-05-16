package server

import (
	"context"
	"net/http"
	"os"
	"sort"

	"github.com/wesm/agentsview/internal/cairn"
	"github.com/wesm/agentsview/internal/db"
	"github.com/wesm/agentsview/internal/service"
)

func cairnOnlyEnabled() bool {
	v := os.Getenv("CAIRN_ONLY")
	return v == "1" || v == "true" || v == "TRUE"
}

func (s *Server) cairnSessionIDs(ctx context.Context) (map[string]struct{}, error) {
	projects, err := s.cairnSessionProjects(ctx)
	if err != nil {
		return nil, err
	}
	ids := make(map[string]struct{}, len(projects))
	for id := range projects {
		ids[id] = struct{}{}
	}
	return ids, nil
}

func (s *Server) cairnSessionProjects(ctx context.Context) (map[string]string, error) {
	runs, err := cairn.ListRuns(ctx, cairn.RunsDirFromEnv(), cairn.ListFilter{})
	if err != nil {
		return nil, err
	}
	projects := make(map[string]string, len(runs))
	for _, run := range runs {
		if run.SessionID != nil && *run.SessionID != "" {
			projects[*run.SessionID] = cairnProjectName(run.ProjectID)
		}
	}
	return projects, nil
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
	projects, err := s.cairnSessionProjects(ctx)
	if err != nil {
		return page, err
	}
	filtered := page.Sessions[:0]
	for _, sess := range page.Sessions {
		if project, ok := projects[sess.ID]; ok {
			if projectFilter != "" && project != projectFilter {
				continue
			}
			sess.Project = project
			filtered = append(filtered, sess)
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
	projects, err := s.cairnSessionProjects(ctx)
	if err != nil {
		return err
	}
	if project, ok := projects[sess.ID]; ok {
		sess.Project = project
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
	projects, err := s.cairnSessionProjects(ctx)
	if err != nil {
		return err
	}
	if project, ok := projects[detail.ID]; ok {
		detail.Project = project
	}
	return nil
}

func (s *Server) cairnProjectInfos(ctx context.Context) ([]db.ProjectInfo, error) {
	projects, err := s.cairnSessionProjects(ctx)
	if err != nil {
		return nil, err
	}
	counts := make(map[string]int)
	for sessionID, project := range projects {
		sess, err := s.db.GetSession(ctx, sessionID)
		if err != nil {
			return nil, err
		}
		if sess == nil {
			continue
		}
		counts[project]++
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
