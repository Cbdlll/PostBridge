import mitt from 'mitt'

type Events = {
    refreshData: void
}

const emitter = mitt<Events>()

export default emitter
