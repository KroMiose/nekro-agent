export const KB_CATEGORY_MAX_LENGTH = 64

export interface FolderImportMetadata {
  category: string
  sourcePath: string
}

export function getFolderImportMetadata(file: Pick<File, 'name' | 'webkitRelativePath'>): FolderImportMetadata {
  const normalizedPath = (file.webkitRelativePath || file.name)
    .replace(/\\/g, '/')
    .split('/')
    .filter(Boolean)
    .join('/')

  if (!normalizedPath) {
    return {
      category: '',
      sourcePath: file.name,
    }
  }

  const directoryPath = normalizedPath.split('/').slice(0, -1).join('/')

  return {
    category: directoryPath ? `${directoryPath}/` : '',
    sourcePath: normalizedPath,
  }
}

export function findCategoryLengthOverflow<T extends { category: string }>(
  items: T[]
): { item: T; length: number } | null {
  for (const item of items) {
    const length = item.category.length
    if (length > KB_CATEGORY_MAX_LENGTH) {
      return { item, length }
    }
  }
  return null
}
