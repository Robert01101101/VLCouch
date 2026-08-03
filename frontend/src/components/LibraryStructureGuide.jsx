function PathExample({ children }) {
  return (
    <pre
      className="mt-2 overflow-x-auto rounded border border-gray-700/60 bg-black/30 px-3 py-2 text-xs leading-relaxed text-gray-300"
    >
      {children}
    </pre>
  )
}

export default function LibraryStructureGuide() {
  return (
    <div data-testid="settings-library-structure-section">
      <h3 className="text-sm font-semibold text-gray-200">Expected file structure</h3>
      <p className="mt-1 text-sm text-gray-400">
        VLCouch scans folders recursively and parses filenames automatically.
      </p>

      <details className="mt-3" data-testid="settings-library-structure-learn-more">
        <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-300">
          Learn more
        </summary>

        <div
          className="mt-4 space-y-5 text-sm text-gray-400"
          data-testid="settings-library-structure-content"
        >
          <div>
            <h4 className="font-medium text-gray-200">Media roots</h4>
            <p className="mt-1">
              Add a <span className="text-gray-300">Movies</span> and/or{' '}
              <span className="text-gray-300">TV</span> folder above.
            </p>
          </div>

          <div>
            <h4 className="font-medium text-gray-200">Movies</h4>
            <p className="mt-1">Title and year come from the filename.</p>
            <PathExample>
              Movies/
              {'\n'}
              {'  '}Harbor Lights (2018).mkv
              {'\n'}
              {'  '}Sunset Ridge (2022)/
              {'\n'}
              {'    '}Sunset Ridge (2022).mkv
              {'\n'}
              {'    '}Sunset Ridge (2022) - Drama - Mystery.txt
            </PathExample>
            <p className="mt-2">
              Optional <span className="text-gray-300">.txt</span> /{' '}
              <span className="text-gray-300">.nfo</span> sidecars can add genre browse rows.
            </p>
          </div>

          <div>
            <h4 className="font-medium text-gray-200">TV shows</h4>
            <p className="mt-1">
              One folder per show. Put <span className="text-gray-300">S01E01</span> (or similar) in
              the filename; the show name comes from the folder.
            </p>
            <PathExample>
              TV/
              {'\n'}
              {'  '}Mystery Manor/
              {'\n'}
              {'    '}Season 01/
              {'\n'}
              {'      '}Mystery Manor - S01E01.mkv
              {'\n'}
              {'  '}[Mystery]/
              {'\n'}
              {'    '}Coastal Patrol/
              {'\n'}
              {'      '}Season 1/
              {'\n'}
              {'        '}Coastal Patrol S01E01 Opening Night.mkv
            </PathExample>
            <p className="mt-2">
              <span className="text-gray-300">[Category]</span> folders group shows into browse
              rows. <span className="text-gray-300">Season 1</span> subfolders are recognized.
            </p>
          </div>

          <div>
            <h4 className="font-medium text-gray-200">Bonus content</h4>
            <p className="mt-1">
              Behind-the-scenes and similar files appear in a Bonus content section on the show
              page.
            </p>
          </div>

          <div>
            <h4 className="font-medium text-gray-200">Subtitles</h4>
            <p className="mt-1">
              Same base name beside the video, or in a <span className="text-gray-300">Subs</span>{' '}
              subfolder.
            </p>
          </div>
        </div>
      </details>
    </div>
  )
}
