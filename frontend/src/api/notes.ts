/** 笔记模块 API（联机 CRUD；离线包读预渲染 JSON） */
import { getJSON, postJSON, isStatic } from './http'

export interface NoteItem {
  name: string
  title: string
  updated: string
  ts: number
  size: number
}

export interface NotesIndex {
  folders: { folder: string; notes: NoteItem[] }[]
}

export interface NoteRendered {
  folder: string
  name: string
  title: string
  html: string
  updated: string
}

const enc = encodeURIComponent

export async function notesIndex(): Promise<NotesIndex> {
  return isStatic() ? getJSON('d/notes/index.json') : getJSON('api/notes/index')
}

export async function noteRendered(folder: string, name: string): Promise<NoteRendered> {
  return isStatic()
    ? getJSON(`d/notes/${enc(folder)}/${enc(name)}.json`)
    : getJSON(`api/notes/render/${enc(folder)}/${enc(name)}`)
}

export const noteContent = (folder: string, name: string) =>
  getJSON<{ folder: string; name: string; title: string; content: string; updated: string }>(
    `api/notes/content/${enc(folder)}/${enc(name)}`)

export const saveNote = (folder: string, name: string, content: string) =>
  postJSON<{ folder: string; name: string }>('api/notes/save', { folder, name, content })

export const createNote = (folder: string, name: string) =>
  postJSON<{ folder: string; name: string }>('api/notes/create', { folder, name })

export const deleteNote = (folder: string, name: string) =>
  postJSON<{ ok: boolean }>('api/notes/delete', { folder, name })

export const renameNote = (folder: string, oldName: string, newName: string) =>
  postJSON<{ folder: string; name: string }>('api/notes/rename', { folder, old: oldName, new: newName })

export const createFolder = (name: string) => postJSON<{ ok: boolean }>('api/notes/folder', { name })

export const renderPreview = (folder: string, name: string, content: string) =>
  postJSON<{ html: string }>('api/notes/render-preview', { folder, name, content })
