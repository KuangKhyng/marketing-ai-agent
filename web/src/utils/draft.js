/**
 * Đếm số phần đang được chọn trong một bản đề xuất.
 *
 * Để riêng file (không nằm trong DraftReview.jsx) vì file component chỉ nên
 * export component — nếu không Fast Refresh của Vite mất tác dụng cho cả file.
 */
export function countChosen(draft, chosen, takeVoice, takeMeta) {
  if (!draft) return 0;
  return (
    Object.values(chosen).filter(Boolean).length +
    (takeVoice && draft.voice_profile ? 1 : 0) +
    (takeMeta && Object.keys(draft.brand_meta || {}).length ? 1 : 0)
  );
}
