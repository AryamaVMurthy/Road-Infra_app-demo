import { useMemo, useState } from 'react'
import { Marker, Popup } from './InteractiveMap'

export function IssueMarkersLayer({
  issues,
  markerColor = '#dc2626',
  onMarkerClick,
  renderPopupContent,
  getIssueKey = (issue) => issue.id,
}) {
  const [selectedIssueId, setSelectedIssueId] = useState(null)

  const validIssues = useMemo(
    () =>
      issues.filter(
        (issue) => Number.isFinite(issue?.lng) && Number.isFinite(issue?.lat)
      ),
    [issues]
  )

  const selectedIssue = useMemo(
    () =>
      validIssues.find((issue) => getIssueKey(issue) === selectedIssueId) || null,
    [validIssues, selectedIssueId, getIssueKey]
  )

  return (
    <>
      {validIssues.map((issue) => {
        const issueKey = getIssueKey(issue)
        return (
          <Marker
            key={issueKey}
            longitude={issue.lng}
            latitude={issue.lat}
            color={markerColor}
            onClick={(event) => {
              event.originalEvent.stopPropagation()
              setSelectedIssueId(issueKey)
              if (onMarkerClick) {
                onMarkerClick(issue)
              }
            }}
          />
        )
      })}

      {selectedIssue && renderPopupContent ? (
        <Popup
          longitude={selectedIssue.lng}
          latitude={selectedIssue.lat}
          closeButton
          closeOnClick={false}
          onClose={() => setSelectedIssueId(null)}
        >
          {renderPopupContent(selectedIssue)}
        </Popup>
      ) : null}
    </>
  )
}
